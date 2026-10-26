from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Forbidden, NotFound, Unprocessable
from app.modules.auth.service import CurrentUser
from app.modules.evals.service import (
    DatasetService,
    LLMClient,
    PromptService,
    RunIn,
    RunService,
    VersionIn,
    VersionOut,
    template_variables,
)
from app.modules.review.critic import CriticFailed, critique
from app.modules.review.models import Review
from app.modules.review.schemas import (
    MAX_REVIEW_CHARS,
    CheckIn,
    CheckOut,
    ReviewIn,
    ReviewOut,
    Rewritten,
)

VARIABLES_CHANGED = (
    "Переписанная версия использует другие переменные — на текущих датасетах она не запустится"
)


def _out(review: Review) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        prompt_id=review.prompt_id,
        prompt_version_id=review.prompt_version_id,
        rewritten_version_id=review.rewritten_version_id,
        cost_usd=review.cost_usd,
        created_at=review.created_at,
        **review.result,
    )


def _rewritten_version(base: VersionIn | VersionOut, rewritten: Rewritten) -> VersionIn:
    """The rewritten texts with the model, effort and limits of the reviewed version."""
    try:
        return VersionIn.model_validate({**base.model_dump(), **rewritten.model_dump()})
    except ValidationError:  # too long for a version
        raise CriticFailed("Критик вернул слишком длинный промпт") from None


class ReviewService:
    def __init__(
        self,
        session: AsyncSession,
        llm: LLMClient,
        prompts: PromptService,
        datasets: DatasetService,
        runs: RunService,
    ) -> None:
        self.session = session
        self.llm = llm
        self.prompts = prompts
        self.datasets = datasets
        self.runs = runs

    async def review(self, user: CurrentUser, body: ReviewIn) -> ReviewOut:
        existing: VersionOut | None = None
        if body.prompt_version_id is None:
            base = VersionIn(
                system=body.system or "",
                user_template=body.user_template or "",
                model="claude-sonnet-5-5",
            )
        else:
            existing = await self.prompts.get_version(user, body.prompt_version_id)
            base = VersionIn.model_validate(existing.model_dump())
            if len(base.system) + len(base.user_template) > MAX_REVIEW_CHARS:
                raise Unprocessable(f"Промпт для ревью не длиннее {MAX_REVIEW_CHARS} символов")

        critic, cost = await critique(self.llm, base.system, base.user_template)
        rewritten = _rewritten_version(base, critic.rewritten)
        changed = template_variables(rewritten.user_template) != template_variables(
            base.user_template
        )

        if existing is not None:
            # nothing is added to the prompt before the user asks to check the rewrite
            prompt_id, version_id, rewritten_id = existing.prompt_id, existing.id, None
        else:
            prompt = await self.prompts.create(
                user, f"Ревью от {datetime.now(UTC).date().isoformat()}", base
            )
            added = await self.prompts.add_version(user, prompt.id, rewritten)
            prompt_id, version_id, rewritten_id = prompt.id, prompt.versions[0].id, added.id

        review = Review(
            owner_id=user.id,
            prompt_id=prompt_id,
            prompt_version_id=version_id,
            rewritten_version_id=rewritten_id,
            result={**critic.model_dump(), "variables_changed": changed},
            cost_usd=cost,
        )
        self.session.add(review)
        await self.session.commit()
        return _out(review)

    async def get(self, user: CurrentUser, review_id: UUID) -> ReviewOut:
        return _out(await self._own(user, review_id))

    async def check(self, user: CurrentUser, review_id: UUID, body: CheckIn) -> CheckOut:
        review = await self._own(user, review_id)
        if review.result["variables_changed"]:
            raise Unprocessable(VARIABLES_CHANGED)
        cases = await self.datasets.get_cases(user, body.dataset_id)
        if review.rewritten_version_id is None:
            await self._add_rewritten(user, review, body)
        assert review.rewritten_version_id is not None

        # shortcut: run B may be refused (cost limit) after run A has started; start both
        # together once the engine can estimate a pair
        run_a, run_b = [
            await self.runs.create_for(
                user.id, version_id, cases, body.graders, "review", dataset_id=body.dataset_id
            )
            for version_id in (review.prompt_version_id, review.rewritten_version_id)
        ]
        return CheckOut(run_a=run_a, run_b=run_b)

    async def _add_rewritten(self, user: CurrentUser, review: Review, body: CheckIn) -> None:
        """Adds the rewrite to the user's prompt, or to a copy of someone else's shared one.

        A copy takes over the review: both runs belong to the reviewer and the author's prompt
        gets none. The reviewed text becomes a version of the copy if the copy's latest differs."""
        original = await self.prompts.get_version(user, review.prompt_version_id)
        # the dataset is refused before anything is added
        await self.runs.estimate(
            user,
            RunIn(prompt_version_id=original.id, dataset_id=body.dataset_id, graders=body.graders),
        )
        rewritten = _rewritten_version(original, Rewritten(**review.result["rewritten"]))
        # shortcut: two checks at once, or a failure after the copy, may leave an extra version or
        # copy; the button is disabled while one runs, lock the review row if it ever happens
        try:
            added = await self.prompts.add_version(user, original.prompt_id, rewritten)
        except Forbidden:  # a shared prompt of someone else: work on a copy of it
            copy = await self.prompts.copy(user, original.prompt_id)
            reviewed = VersionIn.model_validate(original.model_dump())
            baseline = copy.versions[-1]
            if VersionIn.model_validate(baseline.model_dump()) != reviewed:
                baseline = await self.prompts.add_version(user, copy.id, reviewed)
            added = await self.prompts.add_version(user, copy.id, rewritten)
            review.prompt_id, review.prompt_version_id = copy.id, baseline.id
        review.rewritten_version_id = added.id
        await self.session.commit()

    async def _own(self, user: CurrentUser, review_id: UUID) -> Review:
        review = await self.session.scalar(
            select(Review).where(Review.id == review_id, Review.owner_id == user.id)
        )
        if review is None:
            raise NotFound("Не найдено")  # also for someone else's review: no hint that it exists
        return review
