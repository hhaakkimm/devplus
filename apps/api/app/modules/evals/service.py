from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Row, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import BadRequest, NotFound, Unprocessable
from app.modules.auth.service import CurrentUser
from app.modules.evals.access import require_edit, require_view, require_view_run
from app.modules.evals.estimate import estimate_run_cost
from app.modules.evals.graders import Grade, GraderConfig, LlmJudgeGrader, RubricSection
from app.modules.evals.judge import judge
from app.modules.evals.llm import CompletionRequest, LLMClient
from app.modules.evals.models import (
    Dataset,
    DatasetCase,
    Prompt,
    PromptVersion,
    Run,
    RunResult,
    users,
)
from app.modules.evals.pricing import EFFORTS, MODELS
from app.modules.evals.queue import RunQueue
from app.modules.evals.schemas import (
    MAX_CASES,
    MAX_JSONL_BYTES,
    MAX_PROMPT_CHARS,
    CaseIn,
    CaseOut,
    DatasetDetailOut,
    DatasetSummaryOut,
    EstimateOut,
    GradersIn,
    PromptDetailOut,
    PromptSummaryOut,
    ResultOut,
    RunIn,
    RunOut,
    RunSummaryOut,
    VersionIn,
    VersionOut,
)
from app.modules.evals.template import template_variables

# what review and trainer may import from evals: only this module, and only these names
__all__ = [
    "EFFORTS",
    "MAX_PROMPT_CHARS",
    "MODELS",
    "CaseIn",
    "CompletionRequest",
    "DatasetService",
    "Grade",
    "GraderConfig",
    "GradersIn",
    "LLMClient",
    "LlmJudgeGrader",
    "PromptService",
    "RubricSection",
    "RunIn",
    "RunOut",
    "RunService",
    "VersionIn",
    "VersionOut",
    "judge",
    "template_variables",
]

COPY_SUFFIX = " (копия)"
MAX_NAME = 200

_latest_version = (
    select(func.max(PromptVersion.number))
    .where(PromptVersion.prompt_id == Prompt.id)
    .scalar_subquery()
)
# Prompt, owner login, latest version number
_summary_query = select(Prompt, users.c.login, _latest_version).join(
    users, users.c.id == Prompt.owner_id
)


def _copy_name(name: str) -> str:
    return name[: MAX_NAME - len(COPY_SUFFIX)] + COPY_SUFFIX


def _summary(row: Row[Prompt, str, int]) -> PromptSummaryOut:
    prompt, owner_login, latest_version = row
    return PromptSummaryOut(
        id=prompt.id,
        name=prompt.name,
        shared=prompt.shared,
        owner_login=owner_login,
        latest_version=latest_version,
        created_at=prompt.created_at,
    )


class PromptService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user: CurrentUser,
        name: str,
        version: VersionIn,
        trainer_task: str | None = None,
    ) -> PromptDetailOut:
        prompt = Prompt(owner_id=user.id, name=name, trainer_task=trainer_task)
        self.session.add(prompt)
        await self.session.flush()
        self.session.add(
            PromptVersion(prompt_id=prompt.id, number=1, created_by=user.id, **version.model_dump())
        )
        await self.session.commit()
        return await self.get(user, prompt.id)

    async def add_version(
        self, user: CurrentUser, prompt_id: UUID, version: VersionIn
    ) -> VersionOut:
        # the row lock serialises writers, so numbers stay gap-free under UNIQUE(prompt_id, number)
        prompt = await self.session.scalar(
            select(Prompt).where(Prompt.id == prompt_id).with_for_update()
        )
        require_edit(prompt, user.id)
        number = await self.session.scalar(
            select(func.coalesce(func.max(PromptVersion.number), 0) + 1).where(
                PromptVersion.prompt_id == prompt_id
            )
        )
        assert number is not None
        row = PromptVersion(
            prompt_id=prompt_id, number=number, created_by=user.id, **version.model_dump()
        )
        self.session.add(row)
        await self.session.commit()
        return VersionOut.model_validate(row)

    async def get(self, user: CurrentUser, prompt_id: UUID) -> PromptDetailOut:
        row = (await self.session.execute(_summary_query.where(Prompt.id == prompt_id))).first()
        require_view(row[0] if row else None, user.id)
        assert row is not None  # require_view raised otherwise
        versions = await self.session.scalars(
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .order_by(PromptVersion.number)
        )
        return PromptDetailOut(
            **_summary(row).model_dump(), versions=[VersionOut.model_validate(v) for v in versions]
        )

    async def list(self, user: CurrentUser) -> list[PromptSummaryOut]:
        rows = await self.session.execute(
            _summary_query.where(
                or_(Prompt.owner_id == user.id, Prompt.shared), Prompt.trainer_task.is_(None)
            ).order_by(Prompt.created_at.desc(), Prompt.name)
        )
        return [_summary(r) for r in rows]

    async def update(
        self, user: CurrentUser, prompt_id: UUID, name: str | None, shared: bool | None
    ) -> PromptSummaryOut:
        prompt = require_edit(await self.session.get(Prompt, prompt_id), user.id)
        if name is not None:
            prompt.name = name
        if shared is not None:
            prompt.shared = shared
        await self.session.commit()
        row = (await self.session.execute(_summary_query.where(Prompt.id == prompt_id))).one()
        return _summary(row)

    async def copy(self, user: CurrentUser, prompt_id: UUID) -> PromptDetailOut:
        source = await self.get(user, prompt_id)
        latest = VersionIn.model_validate(source.versions[-1].model_dump())
        return await self.create(user, _copy_name(source.name), latest)

    async def get_version(
        self, user: CurrentUser, version_id: UUID, lab_only: bool = False
    ) -> VersionOut:
        """`lab_only`: a version of a Trainer prompt is as hidden as one the user may not see."""
        version = await self.session.get(PromptVersion, version_id)
        prompt = await self.session.get(Prompt, version.prompt_id) if version else None
        prompt = require_view(prompt, user.id)
        if lab_only and prompt.trainer_task is not None:
            raise NotFound("Не найдено")
        assert version is not None
        return VersionOut.model_validate(version)

    async def trainer_prompt_id(self, user: CurrentUser, task: str) -> UUID | None:
        """The user's own prompt for a Trainer task `<module>/<slug>`, once they have tried it."""
        # shortcut: two first attempts at once may make two prompts for a task; harmless, since
        # attempts are found by task_slug; add a unique index (owner_id, trainer_task) if it matters
        return await self.session.scalar(
            select(Prompt.id).where(Prompt.owner_id == user.id, Prompt.trainer_task == task)
        )


_case_count = select(func.count()).where(DatasetCase.dataset_id == Dataset.id).scalar_subquery()
# Dataset, owner login, case count
_dataset_query = select(Dataset, users.c.login, _case_count).join(
    users, users.c.id == Dataset.owner_id
)


def _dataset_summary(row: Row[Dataset, str, int]) -> DatasetSummaryOut:
    dataset, owner_login, case_count = row
    return DatasetSummaryOut(
        id=dataset.id,
        name=dataset.name,
        shared=dataset.shared,
        owner_login=owner_login,
        case_count=case_count,
        created_at=dataset.created_at,
    )


def _case_rows(dataset_id: UUID, cases: Sequence[CaseIn]) -> list[DatasetCase]:
    return [
        DatasetCase(dataset_id=dataset_id, position=i, **c.model_dump())
        for i, c in enumerate(cases, 1)
    ]


def _parse_jsonl(raw: bytes) -> list[CaseIn]:
    if len(raw) > MAX_JSONL_BYTES:
        raise Unprocessable("Файл больше 5 МБ")
    try:
        text = raw.decode("utf-8-sig")  # drops a BOM
    except UnicodeDecodeError:
        raise Unprocessable("Файл не в кодировке UTF-8") from None
    # strip() drops the \r of CRLF; numbers count raw lines, blank ones included
    lines = [(n, s) for n, line in enumerate(text.split("\n"), 1) if (s := line.strip())]
    if len(lines) > MAX_CASES:
        raise Unprocessable(f"В датасете не больше {MAX_CASES} кейсов")
    cases: list[CaseIn] = []
    errors: list[str] = []
    for number, line in lines:
        try:
            cases.append(CaseIn.model_validate_json(line))
        except ValidationError as e:
            problems = (
                ".".join(map(str, p["loc"])) + ": " + p["msg"] if p["loc"] else p["msg"]
                for p in e.errors()
            )
            errors.append(f"Строка {number}: " + ", ".join(problems))
    if errors:
        raise Unprocessable("; ".join(errors))
    return cases


class DatasetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, user: CurrentUser, name: str, cases: Sequence[CaseIn] = ()
    ) -> DatasetDetailOut:
        dataset = Dataset(owner_id=user.id, name=name)
        self.session.add(dataset)
        await self.session.flush()
        self.session.add_all(_case_rows(dataset.id, cases))
        await self.session.commit()
        return await self.get(user, dataset.id)

    async def get(self, user: CurrentUser, dataset_id: UUID) -> DatasetDetailOut:
        row = (await self.session.execute(_dataset_query.where(Dataset.id == dataset_id))).first()
        require_view(row[0] if row else None, user.id)
        assert row is not None  # require_view raised otherwise
        cases = await self.session.scalars(
            select(DatasetCase)
            .where(DatasetCase.dataset_id == dataset_id)
            .order_by(DatasetCase.position)
        )
        return DatasetDetailOut(
            **_dataset_summary(row).model_dump(), cases=[CaseOut.model_validate(c) for c in cases]
        )

    async def update(
        self, user: CurrentUser, dataset_id: UUID, name: str | None, shared: bool | None
    ) -> DatasetSummaryOut:
        dataset = await self._for_edit(user, dataset_id)
        if name is not None:
            dataset.name = name
        if shared is not None:
            dataset.shared = shared
        await self.session.commit()
        row = (await self.session.execute(_dataset_query.where(Dataset.id == dataset_id))).one()
        return _dataset_summary(row)

    async def copy(self, user: CurrentUser, dataset_id: UUID) -> DatasetDetailOut:
        source = await self.get(user, dataset_id)
        cases = [CaseIn(variables=c.variables, expected=c.expected) for c in source.cases]
        return await self.create(user, _copy_name(source.name), cases)

    async def get_cases(self, user: CurrentUser, dataset_id: UUID) -> list[CaseIn]:
        require_view(await self.session.get(Dataset, dataset_id), user.id)
        rows = await self.session.scalars(
            select(DatasetCase)
            .where(DatasetCase.dataset_id == dataset_id)
            .order_by(DatasetCase.position)
        )
        return [CaseIn.model_validate(r, from_attributes=True) for r in rows]

    async def export_jsonl(self, user: CurrentUser, dataset_id: UUID) -> str:
        return "".join(c.model_dump_json() + "\n" for c in await self.get_cases(user, dataset_id))

    async def replace_cases(self, user: CurrentUser, dataset_id: UUID, raw: bytes) -> int:
        await self._for_edit(user, dataset_id)
        cases = _parse_jsonl(raw)  # nothing is written unless every line is valid
        await self.session.execute(delete(DatasetCase).where(DatasetCase.dataset_id == dataset_id))
        self.session.add_all(_case_rows(dataset_id, cases))
        await self.session.commit()
        return len(cases)

    async def add_case(self, user: CurrentUser, dataset_id: UUID, case: CaseIn) -> CaseOut:
        await self._for_edit(user, dataset_id)
        count, last = (
            await self.session.execute(
                select(func.count(), func.coalesce(func.max(DatasetCase.position), 0)).where(
                    DatasetCase.dataset_id == dataset_id
                )
            )
        ).one()
        if count >= MAX_CASES:
            raise Unprocessable(f"В датасете не больше {MAX_CASES} кейсов")
        row = DatasetCase(dataset_id=dataset_id, position=last + 1, **case.model_dump())
        self.session.add(row)
        await self.session.commit()
        return CaseOut.model_validate(row)

    async def update_case(
        self, user: CurrentUser, dataset_id: UUID, case_id: UUID, case: CaseIn
    ) -> CaseOut:
        await self._for_edit(user, dataset_id)
        row = await self._case(dataset_id, case_id)
        row.variables = case.variables
        row.expected = case.expected
        await self.session.commit()
        return CaseOut.model_validate(row)

    async def delete_case(self, user: CurrentUser, dataset_id: UUID, case_id: UUID) -> None:
        await self._for_edit(user, dataset_id)
        await self.session.delete(await self._case(dataset_id, case_id))
        await self.session.commit()

    # keep after every `list[...]` annotation: this method shadows the builtin in the class body
    async def list(self, user: CurrentUser) -> list[DatasetSummaryOut]:
        rows = await self.session.execute(
            _dataset_query.where(or_(Dataset.owner_id == user.id, Dataset.shared)).order_by(
                Dataset.created_at.desc(), Dataset.name
            )
        )
        return [_dataset_summary(r) for r in rows]

    async def _for_edit(self, user: CurrentUser, dataset_id: UUID) -> Dataset:
        # the row lock serialises writers, so positions stay unique and the case limit holds
        dataset = await self.session.scalar(
            select(Dataset).where(Dataset.id == dataset_id).with_for_update()
        )
        return require_edit(dataset, user.id)

    async def _case(self, dataset_id: UUID, case_id: UUID) -> DatasetCase:
        # filtering by dataset_id keeps a case of another dataset unreachable (404)
        row = await self.session.scalar(
            select(DatasetCase).where(
                DatasetCase.id == case_id, DatasetCase.dataset_id == dataset_id
            )
        )
        if row is None:
            raise NotFound("Не найдено")
        return row


# Run and the owner of its prompt, who may see it as well
_run_query = (
    select(Run, Prompt.owner_id)
    .join(PromptVersion, PromptVersion.id == Run.prompt_version_id)
    .join(Prompt, Prompt.id == PromptVersion.prompt_id)
)


class RunService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        llm: LLMClient,
        queue: RunQueue,
        prompts: PromptService,
        datasets: DatasetService,
    ) -> None:
        self.session = session
        self.settings = settings
        self.llm = llm
        self.queue = queue
        self.prompts = prompts
        self.datasets = datasets

    async def estimate(self, user: CurrentUser, body: RunIn) -> EstimateOut:
        version = await self.prompts.get_version(user, body.prompt_version_id)
        cases = await self.datasets.get_cases(user, body.dataset_id)
        estimated, limit = await self._estimate(version, cases, body.graders, body.cost_limit_usd)
        return EstimateOut(estimated_cost_usd=estimated, cost_limit_usd=limit)

    async def create(self, user: CurrentUser, body: RunIn) -> RunOut:
        version = await self.prompts.get_version(user, body.prompt_version_id)
        cases = await self.datasets.get_cases(user, body.dataset_id)
        return await self._start(
            user.id, version, cases, body.graders, "lab", None, body.dataset_id, body.cost_limit_usd
        )

    async def create_for(
        self,
        owner_id: UUID,
        version_id: UUID,
        cases: list[CaseIn],
        graders: list[GraderConfig],
        source: str,
        task_slug: str | None = None,
        dataset_id: UUID | None = None,
        pass_threshold: float | None = None,
    ) -> RunOut:
        """For review and trainer: same checks and limit as `create`, but no access check.

        `pass_threshold` (0..1) makes the run pass or fail as a whole; lab runs have none."""
        row = await self.session.get(PromptVersion, version_id)
        if row is None:
            raise NotFound("Не найдено")
        return await self._start(
            owner_id,
            VersionOut.model_validate(row),
            cases,
            graders,
            source,
            task_slug,
            dataset_id,
            pass_threshold=None if pass_threshold is None else Decimal(str(pass_threshold)),
        )

    async def get(self, user: CurrentUser, run_id: UUID) -> RunOut:
        run, prompt_owner_id = (
            await self.session.execute(_run_query.where(Run.id == run_id))
        ).first() or (None, None)
        run = require_view_run(run, prompt_owner_id, user.id)
        rows = await self.session.scalars(
            select(RunResult).where(RunResult.run_id == run_id).order_by(RunResult.position)
        )
        # Trainer cases are hidden from their author: only the score and the verdict go out
        results = [
            ResultOut(position=r.position, score=r.score, passed=r.passed)
            if run.source == "trainer"
            else ResultOut.model_validate(r)
            for r in rows
        ]
        # errored cases have no real latency, they would drag the percentiles down
        p50, p95 = (
            await self.session.execute(
                select(
                    func.percentile_cont(0.5).within_group(RunResult.latency_ms),
                    func.percentile_cont(0.95).within_group(RunResult.latency_ms),
                ).where(RunResult.run_id == run_id, RunResult.error.is_(None))
            )
        ).one()
        return RunOut.model_validate(run).model_copy(
            update={
                "results": results,
                "latency_p50_ms": None if p50 is None else round(p50),
                "latency_p95_ms": None if p95 is None else round(p95),
            }
        )

    async def passed_tasks(self, owner_id: UUID) -> set[str]:
        """Trainer: the `task_slug` of every task the user has a passed run of."""
        rows = await self.session.scalars(
            select(Run.task_slug).where(
                Run.owner_id == owner_id, Run.source == "trainer", Run.passed.is_(True)
            )
        )
        return {slug for slug in rows if slug is not None}

    # shortcut: no paging, a task with hundreds of attempts sends them all; add a limit then
    async def list_for_task(self, owner_id: UUID, task_slug: str) -> list[RunOut]:
        """Trainer: the user's attempts at a task, newest first, without per-case results."""
        rows = await self.session.scalars(
            select(Run)
            .where(Run.owner_id == owner_id, Run.source == "trainer", Run.task_slug == task_slug)
            .order_by(Run.created_at.desc())
        )
        return [RunOut.model_validate(r) for r in rows]

    # shortcut: no paging, a prompt with hundreds of runs sends them all; add a limit then
    async def list_for_prompt(self, user: CurrentUser, prompt_id: UUID) -> list[RunSummaryOut]:
        prompt = require_view(await self.session.get(Prompt, prompt_id), user.id)
        query = (
            select(Run)
            .join(PromptVersion, PromptVersion.id == Run.prompt_version_id)
            .where(PromptVersion.prompt_id == prompt_id)
            .order_by(Run.created_at.desc())
        )
        if prompt.owner_id != user.id:  # the author sees every run, others only their own
            query = query.where(Run.owner_id == user.id)
        return [RunSummaryOut.model_validate(r) for r in await self.session.scalars(query)]

    async def _estimate(
        self,
        version: VersionOut,
        cases: list[CaseIn],
        graders: Sequence[GraderConfig],
        cost_limit: Decimal | None,
    ) -> tuple[Decimal, Decimal]:
        """Checks the inputs, returns the estimated cost and the limit in force."""
        if not cases:
            raise Unprocessable("В датасете нет кейсов")
        needed = template_variables(version.user_template)
        # positions count from 1 like the snapshot's, not like the stored ones, which may have gaps
        missing = {i: needed - c.variables.keys() for i, c in enumerate(cases, 1)}
        missing = {i: names for i, names in missing.items() if names}
        if missing:
            names = sorted(set().union(*missing.values()))
            raise Unprocessable(
                f"Кейсам {', '.join(map(str, missing))} не хватает переменных: {', '.join(names)}"
            )
        maximum = self.settings.evals_run_cost_limit_usd
        limit = maximum if cost_limit is None else cost_limit
        if limit > maximum:
            raise Unprocessable(f"Лимит прогона не больше ${maximum:.2f}")
        return await estimate_run_cost(self.llm, version, cases, graders), limit

    async def _start(
        self,
        owner_id: UUID,
        version: VersionOut,
        cases: list[CaseIn],
        graders: Sequence[GraderConfig],
        source: str,
        task_slug: str | None,
        dataset_id: UUID | None,
        cost_limit: Decimal | None = None,
        pass_threshold: Decimal | None = None,
    ) -> RunOut:
        estimated, limit = await self._estimate(version, cases, graders, cost_limit)
        if estimated > limit:
            raise BadRequest(f"Ожидаемая стоимость ${estimated:.2f} превышает лимит ${limit:.2f}")
        run = Run(
            owner_id=owner_id,
            prompt_version_id=version.id,
            dataset_id=dataset_id,
            source=source,
            task_slug=task_slug,
            graders=[g.model_dump(mode="json") for g in graders],
            # positions are renumbered: stored ones may have gaps after case deletes
            cases=[
                {"position": i, "variables": c.variables, "expected": c.expected}
                for i, c in enumerate(cases, 1)
            ],
            status="queued",
            cost_limit_usd=limit,
            estimated_cost_usd=estimated,
            cases_total=len(cases),
            pass_threshold=pass_threshold,
        )
        self.session.add(run)
        # commit first: a worker that took the task before the row exists would drop it
        await self.session.commit()
        try:
            await self.queue.enqueue(run.id)
        except Exception:
            # a run that never reached the queue must not wait there to be billed later
            run.status = "failed"
            run.error = "Не удалось поставить в очередь"
            await self.session.commit()
            raise
        return RunOut.model_validate(run)
