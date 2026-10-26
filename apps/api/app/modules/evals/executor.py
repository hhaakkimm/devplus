import asyncio
import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

import anthropic
from pydantic import TypeAdapter
from sqlalchemy import Row, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.evals.graders import Grade, GraderConfig, case_result, grade
from app.modules.evals.llm import CompletionRequest, LLMClient
from app.modules.evals.models import PromptVersion, Run, RunResult
from app.modules.evals.schemas import VersionOut
from app.modules.evals.template import MissingVariable, render

logger = logging.getLogger(__name__)

INTERRUPTED = "Прерван: worker перезапущен"
ALL_FAILED = "Все кейсы завершились ошибкой"
CRASHED = "Внутренняя ошибка"
MAX_ERROR = 500

_graders = TypeAdapter(list[GraderConfig])
Log = logging.LoggerAdapter[logging.Logger]


class RunExecutor:
    """Runs a queued run case by case. Writes go through one session, one at a time."""

    def __init__(self, session: AsyncSession, llm: LLMClient, settings: Settings) -> None:
        self.session = session
        self.llm = llm
        self.settings = settings

    async def execute(self, run_id: UUID) -> None:
        # a LoggerAdapter puts `run_id` on every record, as `extra={"run_id": ...}` would
        log: Log = logging.LoggerAdapter(logger, {"run_id": str(run_id)})
        claimed = await self._claim(run_id)
        if claimed is None:
            log.info("skipped: the run is not queued")
            return
        log.info("started: %d cases", len(claimed.cases))
        try:
            over_budget = await self._run_cases(run_id, claimed, log)
            await self._finish(run_id, claimed.pass_threshold, len(claimed.cases), over_budget, log)
        except Exception:
            # not left `running` until the next worker start: the caller is told, and so is the run
            log.exception("crashed")
            await self.session.rollback()
            await self._fail(run_id, CRASHED)

    async def recover(self) -> tuple[int, list[UUID]]:
        """At worker start: runs left `running` are failed, `queued` ones are returned to resend.

        Redis may have lost their messages, and sending twice is safe: `execute` is idempotent.
        """
        interrupted = await self.session.scalars(
            update(Run)
            .where(Run.status == "running")
            .values(status="failed", error=INTERRUPTED, finished_at=func.now())
            .returning(Run.id)
        )
        queued = await self.session.scalars(
            select(Run.id).where(Run.status == "queued").order_by(Run.created_at)
        )
        count, ids = len(interrupted.all()), list(queued)
        await self.session.commit()
        return count, ids

    async def _claim(self, run_id: UUID) -> Row[Any] | None:
        """queued -> running in one statement: of two workers taking the same run, one gets it."""
        claimed = await self.session.execute(
            update(Run)
            .where(Run.id == run_id, Run.status == "queued")
            .values(status="running", started_at=func.now())
            .returning(
                Run.prompt_version_id,
                Run.graders,
                Run.cases,
                Run.cost_limit_usd,
                Run.pass_threshold,
            )
        )
        row = claimed.first()
        await self.session.commit()
        return row

    async def _run_cases(self, run_id: UUID, run: Row[Any], log: Log) -> bool:
        """Runs the cases, at most `evals_concurrency` at once. True if the cost limit was hit."""
        # copied out of the ORM: the session is committed under these tasks all along
        version = VersionOut.model_validate(
            await self.session.get_one(PromptVersion, run.prompt_version_id)
        )
        graders = _graders.validate_python(run.graders)
        slots = asyncio.Semaphore(self.settings.evals_concurrency)
        writing = asyncio.Lock()
        over_budget = asyncio.Event()

        async def one(case: dict[str, Any]) -> None:
            async with slots:
                if over_budget.is_set():  # decided at the start, so a late slot does not spend more
                    return
                result = await self._run_case(run_id, version, graders, case)
                async with writing:
                    self.session.add(result)
                    total = await self.session.scalar(
                        update(Run)
                        .where(Run.id == run_id)
                        .values(
                            cases_done=Run.cases_done + 1, cost_usd=Run.cost_usd + result.cost_usd
                        )
                        .returning(Run.cost_usd)
                    )
                    await self.session.commit()
                if result.error:
                    log.warning("case %d failed: %s", result.position, result.error)
                if total is not None and total > run.cost_limit_usd:
                    over_budget.set()
                    log.warning("over budget: $%s of $%s", total, run.cost_limit_usd)

        async with asyncio.TaskGroup() as group:
            for case in run.cases:
                group.create_task(one(case))
        return over_budget.is_set()

    async def _run_case(
        self, run_id: UUID, version: VersionOut, graders: list[GraderConfig], case: dict[str, Any]
    ) -> RunResult:
        """The result row of one case. Its failures are its own `error`, never the run's."""
        variables, expected = case["variables"], case["expected"]
        result = RunResult(
            run_id=run_id,
            position=case["position"],
            input_vars=variables,
            output="",
            output_json=None,
            truncated=False,
            grades=[],
            score=Decimal(0),
            passed=False,
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            cost_usd=Decimal(0),
            latency_ms=0,
            error=None,
        )
        try:
            user = render(version.user_template, variables)
        except MissingVariable as e:  # the dataset was edited after the run was checked
            result.error = f"Нет переменной {e.name}"
            return result
        try:
            completion = await self.llm.complete(
                CompletionRequest(
                    model=version.model,
                    system=version.system,
                    user=user,
                    effort=version.effort,
                    max_tokens=version.max_tokens,
                    output_schema=version.output_schema,
                )
            )
        except anthropic.APIError as e:  # the SDK has already retried
            result.error = str(e)[:MAX_ERROR]
            return result

        result.output = completion.text
        result.output_json = completion.json
        result.truncated = completion.stop_reason == "max_tokens"  # graded as it is
        result.input_tokens = completion.input_tokens
        result.output_tokens = completion.output_tokens
        result.cache_read_tokens = completion.cache_read_tokens
        result.cost_usd = completion.cost_usd
        result.latency_ms = completion.latency_ms
        if completion.stop_reason == "refusal":
            category = f" ({completion.refusal_category})" if completion.refusal_category else ""
            result.error = f"Модель отказалась отвечать{category}"
            return result

        grades: list[Grade] = []
        try:
            for cfg in graders:
                grades.append(
                    await grade(
                        cfg,
                        inputs=variables,
                        expected=expected,
                        output=completion.text,
                        llm=self.llm,
                    )
                )
        except anthropic.APIError as e:  # only the judge calls the API
            result.error = str(e)[:MAX_ERROR]
        result.grades = [g.to_json() for g in grades]
        result.cost_usd += sum((g.cost_usd for g in grades), Decimal(0))  # the judge is paid too
        if result.error is None:
            score, result.passed = case_result(grades)
            result.score = Decimal(str(score))
        return result

    async def _finish(
        self,
        run_id: UUID,
        pass_threshold: Decimal | None,
        cases_total: int,
        over_budget: bool,
        log: Log,
    ) -> None:
        done, score_avg, passed, errors = (
            await self.session.execute(
                select(
                    func.count(),
                    func.avg(RunResult.score),
                    func.count().filter(RunResult.passed),
                    func.count().filter(RunResult.error.is_not(None)),
                ).where(RunResult.run_id == run_id)
            )
        ).one()
        status = "over_budget" if over_budget else "failed" if errors == done else "done"
        pass_rate = Decimal(passed) / done if done else None
        values: dict[str, Any] = {
            "status": status,
            "score_avg": score_avg,
            "pass_rate": pass_rate,
            "finished_at": func.now(),
        }
        if status == "failed":
            values["error"] = ALL_FAILED
        if pass_threshold is not None:
            # Trainer: counts only if every hidden case was graded. A run cut short cannot pass,
            # but one whose last case tipped it over budget has graded them all
            values["passed"] = (
                done == cases_total and status != "failed" and (pass_rate or 0) >= pass_threshold
            )
        cost = await self.session.scalar(
            update(Run).where(Run.id == run_id).values(**values).returning(Run.cost_usd)
        )
        await self.session.commit()
        log.info("finished: %s, %d cases, $%s", status, done, cost)

    async def _fail(self, run_id: UUID, reason: str) -> None:
        await self.session.execute(
            update(Run)
            .where(Run.id == run_id)
            .values(status="failed", error=reason, finished_at=func.now())
        )
        await self.session.commit()
