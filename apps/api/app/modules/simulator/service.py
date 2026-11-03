import asyncio
import logging
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import BadRequest, DomainError, NotFound, Unprocessable
from app.modules.auth.service import CurrentUser
from app.modules.evals.service import LLM_ERRORS, Grade, LLMClient
from app.modules.simulator.engine.catalog import CATALOG
from app.modules.simulator.engine.graph import structural_errors
from app.modules.simulator.engine.lint import lint
from app.modules.simulator.engine.scenarios import ScenarioResult, run_scenario
from app.modules.simulator.models import SimAttempt
from app.modules.simulator.review import estimate_review, review_attempt, review_request
from app.modules.simulator.schemas import (
    SimAnswers,
    SimAttemptIn,
    SimAttemptOut,
    SimComponentOut,
    SimFindingOut,
    SimGraph,
    SimNodeMetricsOut,
    SimParamOut,
    SimReviewOut,
    SimReviewSectionOut,
    SimRunIn,
    SimRunOut,
    SimScale,
    SimScenarioOut,
    SimTaskOut,
    SimTaskSummaryOut,
    SimVerdictOut,
    SimVisibleScenarioOut,
)
from app.modules.simulator.tasks import SimTask, cached_sim_tasks

logger = logging.getLogger(__name__)

DAILY_LIMIT = 20
DAY = timedelta(hours=24)
COST_LIMIT = Decimal("0.10")
# 16 000 tokens of thinking take a few minutes; a call still running after this one has hung
JUDGE_TIMEOUT = timedelta(minutes=9)
UNAVAILABLE = "AI-разбор не удался: Claude API недоступен"


class SubmitLimitReached(DomainError):
    status_code = 429


class GraphNotRunnable(Unprocessable):
    pass


class ReviewTooExpensive(BadRequest):
    pass


def _scenario_out(r: ScenarioResult) -> SimScenarioOut:
    # an explicit list: `visible` stays out, and a field added to ScenarioResult stays hidden
    return SimScenarioOut(
        id=r.id,
        title=r.title,
        passed=r.passed,
        latency_ms=r.latency_ms,
        error_rate=r.error_rate,
        rejected_rate=r.rejected_rate,
        message_loss=r.message_loss,
        bottleneck=r.bottleneck,
        explanation=r.explanation,
        nodes=[SimNodeMetricsOut(**asdict(m)) for m in r.nodes.values()],
    )


def _key(t: SimTask) -> str:
    return f"{t.module}/{t.slug}"


def _attempt_out(a: SimAttempt) -> SimAttemptOut:
    # explicit lists: whatever else a stored scenario holds (its numbers) stays on the server
    # shortcut: old attempts are revalidated against the current catalog, a narrowed param would
    # 500 the history; store graphs unvalidated or migrate them if the catalog ever narrows
    return SimAttemptOut(
        id=a.id,
        created_at=a.created_at,
        graph=SimGraph.model_validate(a.graph),
        answers=SimAnswers.model_validate(a.answers),
        scenarios=[
            SimVerdictOut(
                id=s["id"],
                title=s["title"],
                visible=s["visible"],
                passed=s["passed"],
                explanation=s["explanation"],
            )
            for s in a.scenarios
        ],
        findings=[SimFindingOut.model_validate(f) for f in a.findings],
        review=None if a.review is None else SimReviewOut.model_validate(a.review),
        review_error=a.review_error,
        score=None if a.score is None else float(a.score),
        passed=a.passed,
        cost_usd=a.cost_usd,
    )


def _review_out(t: SimTask, grade: Grade) -> SimReviewOut:
    """A judged review, its sections in the order of the rubric."""
    by_name = {s["name"]: s for s in grade.sections or []}
    return SimReviewOut(
        score=grade.score,
        passed=grade.passed,
        sections=[
            SimReviewSectionOut(
                name=r.name, score=by_name[r.name]["score"], comment=by_name[r.name]["reason"]
            )
            for r in t.review.rubric
        ],
        comment=grade.comment or "",
    )


class SimulatorService:
    def __init__(self, session: AsyncSession, settings: Settings, llm: LLMClient) -> None:
        self.session = session
        self.settings = settings
        self.llm = llm  # for the AI review of a submission

    def components(self) -> list[SimComponentOut]:
        return [
            SimComponentOut(
                type=c.type,
                label=c.label,
                description=c.description,
                capacity_rps=c.capacity_rps,
                latency_ms=c.latency_ms,
                params=[SimParamOut(**asdict(p)) for p in c.params],
            )
            for c in CATALOG.values()
        ]

    async def tasks(self, user: CurrentUser) -> list[SimTaskSummaryOut]:
        solved = set(
            await self.session.scalars(
                select(SimAttempt.task_key)
                .where(SimAttempt.user_id == user.id, SimAttempt.passed)
                .distinct()
            )
        )
        return [
            SimTaskSummaryOut(
                module=t.module,
                slug=t.slug,
                title=t.title,
                summary=t.summary,
                solved=_key(t) in solved,
            )
            for t in self._tasks()
        ]

    def task(self, module: str, slug: str) -> SimTaskOut:
        t = self._task(module, slug)
        # the schema is the whitelist: attributes it does not list (`visible`, targets of hidden
        # scenarios, `review`, `reference_graph`) never reach the response
        return SimTaskOut(
            module=t.module,
            slug=t.slug,
            title=t.title,
            summary=t.summary,
            scale=SimScale.model_validate(t.scale, from_attributes=True),
            scenarios=[
                SimVisibleScenarioOut.model_validate(s, from_attributes=True)
                for s in t.scenarios
                if s.visible
            ],
        )

    def run(self, module: str, slug: str, body: SimRunIn) -> SimRunOut:
        """Visible scenarios only, nothing is stored. An `EngineError` is a bug, so a 500."""
        t = self._task(module, slug)
        graph = body.graph
        if errors := structural_errors(graph):
            return SimRunOut(structural_errors=errors, scenarios=[], findings=[])
        return SimRunOut(
            structural_errors=[],
            scenarios=[
                _scenario_out(run_scenario(graph, t.scale.peak_rps, t.scale.read_ratio, s))
                for s in t.scenarios
                if s.visible
            ],
            findings=[SimFindingOut(**asdict(f)) for f in lint(graph, t.scale.read_ratio)],
        )

    async def submit(
        self, user: CurrentUser, module: str, slug: str, body: SimAttemptIn
    ) -> SimAttemptOut:
        """Every scenario, the rules and the AI review. The attempt is stored before the judge is
        called and completed after it, so it counts toward the daily limit while the call runs;
        a failed review leaves it with `review_error`."""
        t = self._task(module, slug)
        graph = body.graph
        if errors := structural_errors(graph):
            raise GraphNotRunnable("Схема не прогоняется: " + "; ".join(errors))
        scale = t.scale
        results = [run_scenario(graph, scale.peak_rps, scale.read_ratio, s) for s in t.scenarios]
        findings = lint(graph, scale.read_ratio)
        cfg, req, inputs, output = review_request(t, graph, results, findings, body.answers)
        attempt = SimAttempt(
            id=uuid4(),
            user_id=user.id,
            task_key=_key(t),
            graph=graph.model_dump(mode="json"),
            answers=body.answers.model_dump(),
            # the results without per-node metrics; a scenario's targets are not part of them
            scenarios=[{k: v for k, v in asdict(r).items() if k != "nodes"} for r in results],
            findings=[asdict(f) for f in findings],
            review=None,
            review_error=None,
            score=None,
            passed=False,
            cost_usd=Decimal(0),
        )
        extra = {"attempt_id": str(attempt.id), "task_key": attempt.task_key}  # no student text
        await self.session.commit()  # no transaction is held during the calls to Claude
        # shortcut: синхронный вызов Claude, перенести в worker, если ответы станут дольше минуты
        estimated: Decimal | None = None
        try:
            async with asyncio.timeout(JUDGE_TIMEOUT.total_seconds()):
                estimated = await estimate_review(self.llm, req)
        except (*LLM_ERRORS, TimeoutError):  # the SDK has already retried; the judge is skipped
            logger.warning("review call failed", exc_info=True, extra=extra)
            attempt.review_error = UNAVAILABLE
        if estimated is not None and estimated > COST_LIMIT:  # before the claim: nothing stored
            raise ReviewTooExpensive(
                f"Ожидаемая стоимость разбора ${estimated:.2f} выше лимита ${COST_LIMIT:.2f}"
            )
        await self._claim(user, attempt)
        grade: Grade | None = None
        if attempt.review_error is None:
            try:
                async with asyncio.timeout(JUDGE_TIMEOUT.total_seconds()):
                    grade = await review_attempt(self.llm, t, cfg, inputs, output)
            except (*LLM_ERRORS, TimeoutError):  # the SDK has already retried
                logger.warning("review call failed", exc_info=True, extra=extra)
                attempt.review_error = UNAVAILABLE
        if grade is not None:
            attempt.cost_usd = grade.cost_usd  # paid even when failed
            if grade.error is not None:
                logger.warning("review failed: %s", grade.error, extra=extra)
                attempt.review_error = f"AI-разбор не удался: {grade.error}"
            else:
                review = _review_out(t, grade)
                attempt.review = review.model_dump()
                attempt.score = Decimal(str(review.score))
                attempt.passed = (
                    all(r.passed for r in results)
                    and not any(f.severity == "critical" for f in findings)
                    and review.passed
                )
        await self.session.commit()
        await self.session.refresh(attempt)
        return _attempt_out(attempt)

    async def _claim(self, user: CurrentUser, attempt: SimAttempt) -> None:
        """Stores the attempt if the daily limit allows; over the limit nothing is stored."""
        # one claim per user at a time: the count sees every claim committed before this one
        await self.session.execute(
            select(func.pg_advisory_xact_lock(func.hashtext(f"simulator:{user.id}")))
        )
        # shortcut: лимит в коде, вынести в настройки при публичном запуске
        # shortcut: an attempt whose process died mid-review (or hit an unexpected error) keeps
        # no review and no review_error, so it counts for 24 h; sweep stale ones if that shows up
        sent = await self.session.scalar(
            select(func.count())
            .select_from(SimAttempt)
            .where(
                SimAttempt.user_id == user.id,
                SimAttempt.created_at > func.now() - DAY,
                # in flight, reviewed, or failed after the judge was paid; a free outage is not
                or_(SimAttempt.review_error.is_(None), SimAttempt.cost_usd > 0),
            )
        )
        if (sent or 0) >= DAILY_LIMIT:
            raise SubmitLimitReached("Лимит отправок на сегодня исчерпан")
        self.session.add(attempt)
        await self.session.commit()  # before the judge: no transaction is held during its call

    async def attempts(self, user: CurrentUser, module: str, slug: str) -> list[SimAttemptOut]:
        """The user's own attempts at the task, newest first."""
        t = self._task(module, slug)
        rows = await self.session.scalars(
            select(SimAttempt)
            .where(SimAttempt.user_id == user.id, SimAttempt.task_key == _key(t))
            .order_by(SimAttempt.created_at.desc(), SimAttempt.id)
        )
        return [_attempt_out(a) for a in rows]

    def _tasks(self) -> tuple[SimTask, ...]:
        return cached_sim_tasks(Path(self.settings.content_dir))

    def _task(self, module: str, slug: str) -> SimTask:
        # matched against the loaded list only: the URL never becomes a path
        for t in self._tasks():
            if (t.module, t.slug) == (module, slug):
                return t
        raise NotFound("Не найдено")
