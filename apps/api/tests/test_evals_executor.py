import asyncio
import importlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from decimal import Decimal
from uuid import UUID

import anthropic
import httpx
import pytest
from dishka.integrations.taskiq import TaskiqProvider
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import InMemoryBroker, TaskiqEvents

from app.core.config import Settings
from app.core.container import build_container
from app.modules.evals.executor import RunExecutor
from app.modules.evals.graders import LlmJudgeGrader, RubricSection
from app.modules.evals.judge import JUDGE_SYSTEM, judge_user
from app.modules.evals.llm import Completion, CompletionRequest, FakeLLMClient
from app.modules.evals.models import Run, RunResult
from app.modules.evals.queue import TASK_NAME, TaskiqRunQueue
from tests.conftest import TEST_DATABASE_URL

HAIKU_CASE_COST = Decimal("0.000035")  # FakeLLMClient: 100 in + 50 out on haiku
JUDGE = LlmJudgeGrader(
    type="llm_judge",
    rubric=[RubricSection(name="A", description="d")],
    model="claude-haiku-5-5",
)


def api_error(message: str = "boom") -> anthropic.APIError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIConnectionError(message=message, request=request)


@dataclass
class Scripted:
    """The fake LLM, with a hook to raise for or reshape the answer to chosen requests."""

    raises: Callable[[CompletionRequest], Exception | None] = lambda req: None
    reshape: Callable[[CompletionRequest, Completion], Completion] = lambda req, c: c
    inner: FakeLLMClient = field(default_factory=FakeLLMClient)

    async def complete(self, req: CompletionRequest) -> Completion:
        if (exc := self.raises(req)) is not None:
            raise exc
        return self.reshape(req, await self.inner.complete(req))

    async def count_tokens(self, req: CompletionRequest) -> int:
        return await self.inner.count_tokens(req)


async def results(db: AsyncSession, run: Run) -> list[RunResult]:
    rows = await db.scalars(
        select(RunResult).where(RunResult.run_id == run.id).order_by(RunResult.position)
    )
    return list(rows)


async def test_execute_scores_and_finishes(db_session, fake_llm, run_executor, make_run):
    run = await make_run()
    await run_executor.execute(run.id)
    await db_session.refresh(run)
    assert (run.status, run.cases_done, run.score_avg, run.pass_rate) == ("done", 2, 1, 1)
    assert run.cost_usd == 2 * HAIKU_CASE_COST
    assert run.started_at and run.finished_at and run.error is None
    assert run.passed is None  # a lab run has no pass threshold
    first, second = await results(db_session, run)
    assert (first.position, first.input_vars, first.output) == (1, {"name": "a"}, "a")
    assert (first.score, first.passed, first.truncated, first.error) == (1, True, False, None)
    assert (first.input_tokens, first.output_tokens, first.cost_usd) == (100, 50, HAIKU_CASE_COST)
    assert first.grades[0]["type"] == "exact" and second.output == "b"
    assert len(fake_llm.calls) == 2


async def test_execute_is_idempotent(db_session, fake_llm, run_executor, make_run):
    run = await make_run()
    await run_executor.execute(run.id)
    await run_executor.execute(run.id)
    await db_session.refresh(run)
    assert len(fake_llm.calls) == 2 and len(await results(db_session, run)) == 2
    assert (run.status, run.cases_done) == ("done", 2)
    for status in ("running", "failed", "over_budget"):
        other = await make_run(status=status)
        await run_executor.execute(other.id)
        assert (await results(db_session, other)) == [] and len(fake_llm.calls) == 2


async def test_failed_cases_are_scored_zero(db_session, settings, make_run):
    llm = Scripted(raises=lambda req: api_error("rate limited") if req.user == "b" else None)
    run = await make_run()
    await RunExecutor(db_session, llm, settings).execute(run.id)
    await db_session.refresh(run)
    ok, bad = await results(db_session, run)
    assert (ok.score, ok.error) == (1, None)
    assert (bad.score, bad.passed, bad.error, bad.cost_usd) == (0, False, "rate limited", 0)
    # the failed case counts as done, and drags the averages down
    assert (run.status, run.cases_done, run.score_avg, run.pass_rate) == ("done", 2, 0.5, 0.5)
    assert run.cost_usd == HAIKU_CASE_COST


async def test_case_error_text_is_cut_to_500_chars(db_session, settings, make_run):
    run = await make_run()
    llm = Scripted(raises=lambda req: api_error("x" * 900))
    await RunExecutor(db_session, llm, settings).execute(run.id)
    assert {r.error for r in await results(db_session, run)} == {"x" * 500}


async def test_all_cases_error_is_failed(db_session, settings, make_run):
    run = await make_run()
    await RunExecutor(db_session, Scripted(raises=lambda req: api_error()), settings).execute(
        run.id
    )
    await db_session.refresh(run)
    assert (run.status, run.cases_done, run.cost_usd) == ("failed", 2, 0)
    assert run.error == "Все кейсы завершились ошибкой" and run.finished_at


async def test_missing_variable_is_case_error(db_session, fake_llm, run_executor, make_run):
    run = await make_run(
        [
            {"variables": {"name": "a", "tone": "x"}, "expected": "a x"},
            {"variables": {"name": "b"}, "expected": "b"},  # the dataset was edited after the check
        ],
        template="{{name}} {{tone}}",
    )
    await run_executor.execute(run.id)
    await db_session.refresh(run)
    ok, bad = await results(db_session, run)
    assert ok.error is None and (bad.error, bad.score, bad.passed) == (
        "Нет переменной tone",
        0,
        False,
    )
    assert bad.input_vars == {"name": "b"} and len(fake_llm.calls) == 1 and run.status == "done"


async def test_refusal_and_truncation(db_session, settings, make_run):
    def reshape(req: CompletionRequest, c: Completion) -> Completion:
        if req.user == "a":
            return replace(c, text="", stop_reason="refusal", refusal_category="cyber")
        return replace(c, stop_reason="max_tokens")

    run = await make_run()
    await RunExecutor(db_session, Scripted(reshape=reshape), settings).execute(run.id)
    await db_session.refresh(run)
    refused, cut = await results(db_session, run)
    assert refused.error == "Модель отказалась отвечать (cyber)"
    assert (refused.score, refused.passed) == (0, False)
    assert refused.cost_usd == HAIKU_CASE_COST  # the tokens were spent
    # a cut-off answer is graded as it is
    assert (cut.truncated, cut.error, cut.score, cut.passed) == (True, None, 1, True)
    assert run.status == "done"


async def test_over_budget_stops_new_cases(db_session, fake_llm, settings, make_run):
    cases = [{"variables": {"name": str(i)}, "expected": str(i)} for i in range(5)]
    # one case costs more than the whole limit; with one at a time, the second never starts
    run = await make_run(cases, cost_limit_usd="0.00001", pass_threshold="0.5")
    await RunExecutor(
        db_session, fake_llm, settings.model_copy(update={"evals_concurrency": 1})
    ).execute(run.id)
    await db_session.refresh(run)
    assert (run.status, run.cases_done, run.cases_total) == ("over_budget", 1, 5)
    assert len(await results(db_session, run)) == 1 and len(fake_llm.calls) == 1
    assert (run.score_avg, run.pass_rate) == (1, 1)  # over the finished cases
    assert run.passed is False  # a partial run cannot pass
    assert run.cost_usd == HAIKU_CASE_COST and run.finished_at


def test_zero_concurrency_is_refused(settings):
    # a semaphore of 0 would park every case forever
    with pytest.raises(ValidationError):
        Settings(**{**settings.model_dump(), "evals_concurrency": 0})


async def test_concurrency_is_bounded(db_session, settings, make_run):
    in_flight = peak = 0

    class Slow(FakeLLMClient):
        async def complete(self, req: CompletionRequest) -> Completion:
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.01)
            in_flight -= 1
            return await super().complete(req)

    cases = [{"variables": {"name": str(i)}, "expected": str(i)} for i in range(6)]
    run = await make_run(cases)
    await RunExecutor(
        db_session, Slow(), settings.model_copy(update={"evals_concurrency": 2})
    ).execute(run.id)
    await db_session.refresh(run)
    assert (peak, run.status, run.cases_done) == (2, "done", 6)


@pytest.mark.parametrize(
    ("threshold", "passed"), [("0.5", True), ("0.6", False), ("0", True), ("1", False)]
)
async def test_trainer_threshold_sets_passed(run_executor, db_session, make_run, threshold, passed):
    run = await make_run(
        [
            {"variables": {"name": "a"}, "expected": "a"},
            {"variables": {"name": "b"}, "expected": "not b"},
        ],
        source="trainer",
        pass_threshold=threshold,
    )
    await run_executor.execute(run.id)
    await db_session.refresh(run)
    assert (run.status, run.pass_rate, run.passed) == ("done", 0.5, passed)


async def test_trainer_run_over_budget_on_its_last_case_still_counts(
    db_session, fake_llm, settings, make_run
):
    # the second case takes the cost over the limit, but there was no third one left to skip
    run = await make_run(source="trainer", pass_threshold="0.5", cost_limit_usd="0.00005")
    await RunExecutor(
        db_session, fake_llm, settings.model_copy(update={"evals_concurrency": 1})
    ).execute(run.id)
    await db_session.refresh(run)
    assert (run.status, run.cases_done, run.cases_total) == ("over_budget", 2, 2)
    assert (run.pass_rate, run.passed) == (1, True)


async def test_failed_run_does_not_pass_a_zero_threshold(db_session, settings, make_run):
    run = await make_run(pass_threshold="0")
    await RunExecutor(db_session, Scripted(raises=lambda req: api_error()), settings).execute(
        run.id
    )
    await db_session.refresh(run)
    assert (run.status, run.passed) == ("failed", False)


async def test_judge_cost_counts_and_judge_error_is_case_error(db_session, settings, make_run):
    verdict = json.dumps({"sections": [{"name": "A", "score": 5, "reason": "r"}], "comment": "ok"})
    inner = FakeLLMClient({judge_user(JUDGE, {"name": "a"}, "a", "a"): verdict})
    llm = Scripted(
        inner=inner,
        raises=lambda req: (
            api_error("judge down")
            if req.system == JUDGE_SYSTEM and "<response>\nb\n" in req.user
            else None
        ),
    )
    run = await make_run(graders=[{"type": "exact"}, JUDGE.model_dump(mode="json")])
    await RunExecutor(db_session, llm, settings).execute(run.id)
    await db_session.refresh(run)
    ok, bad = await results(db_session, run)
    assert (ok.score, ok.passed, ok.error) == (1, True, None)
    assert ok.cost_usd == 2 * HAIKU_CASE_COST  # the answer and the judge
    assert (bad.error, bad.score, bad.passed) == ("judge down", 0, False)
    assert bad.output == "b" and bad.cost_usd == HAIKU_CASE_COST  # the answer was paid for
    assert (run.status, run.cases_done, run.cost_usd) == ("done", 2, 3 * HAIKU_CASE_COST)


async def test_unexpected_error_fails_the_run(db_session, settings, make_run, caplog):
    run = await make_run()
    llm = Scripted(raises=lambda req: RuntimeError("bug"))
    with caplog.at_level(logging.INFO, logger="app.modules.evals.executor"):
        await RunExecutor(db_session, llm, settings).execute(run.id)
    await db_session.refresh(run)
    assert (run.status, run.error) == ("failed", "Внутренняя ошибка") and run.finished_at
    # every line the executor logs says which run it is about
    lines = [r for r in caplog.records if r.name == "app.modules.evals.executor"]
    assert lines and {r.run_id for r in lines} == {str(run.id)}
    assert any(r.exc_info for r in lines)


async def test_recover_marks_running_and_requeues_queued(db_session, run_executor, make_run):
    running = await make_run(status="running")
    queued = [await make_run(), await make_run()]
    done = await make_run(status="done")
    failed, requeue = await run_executor.recover()
    assert failed == 1 and sorted(requeue) == sorted(r.id for r in queued)
    for run in (running, done, *queued):
        await db_session.refresh(run)
    assert (running.status, running.error) == ("failed", "Прерван: worker перезапущен")
    assert running.finished_at is not None
    assert (done.status, [r.status for r in queued]) == ("done", ["queued", "queued"])
    # a second start finds nothing left to fail, and the same runs still waiting
    again, still_queued = await run_executor.recover()
    assert again == 0 and sorted(still_queued) == sorted(requeue)


def import_worker(monkeypatch: pytest.MonkeyPatch):
    # worker.py builds its Settings and broker at import, the way main.py does for the app
    env = {
        "DATABASE_URL": TEST_DATABASE_URL,
        "GITHUB_CLIENT_ID": "x",
        "GITHUB_CLIENT_SECRET": "x",
        "APP_ORIGIN": "http://testserver",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return importlib.import_module("app.worker")


async def test_taskiq_task_runs_executor_inmemory(
    monkeypatch, db_session, fake_llm, settings, overrides, make_run
):
    broker = InMemoryBroker(await_inplace=True)
    container = build_container(settings, *overrides, TaskiqProvider())
    import_worker(monkeypatch).setup_worker(broker, container)
    # the in-memory broker fires the worker's startup handlers on the API side too
    broker.event_handlers.pop(TaskiqEvents.WORKER_STARTUP)
    run = await make_run()

    queue = TaskiqRunQueue(broker)  # what the API sends through: the task is found by its name
    await queue.enqueue(run.id)

    await db_session.refresh(run)
    assert (run.status, run.cases_done, len(fake_llm.calls)) == ("done", 2, 2)
    await queue.close()
    await container.close()


async def test_worker_startup_recovers_runs(monkeypatch, db_session, settings, overrides, make_run):
    broker = InMemoryBroker(await_inplace=True)
    container = build_container(settings, *overrides, TaskiqProvider())
    import_worker(monkeypatch).setup_worker(broker, container)
    interrupted, waiting = await make_run(status="running"), await make_run()

    await broker.startup()

    await db_session.refresh(interrupted)
    await db_session.refresh(waiting)
    assert (interrupted.status, interrupted.error) == ("failed", "Прерван: worker перезапущен")
    assert (waiting.status, waiting.cases_done) == ("done", 2)  # put back on the queue and run
    await container.close()


async def test_queue_starts_the_broker_once_under_concurrent_first_sends():
    class CountingBroker(InMemoryBroker):
        starts = 0

        async def startup(self) -> None:
            self.starts += 1
            await asyncio.sleep(0.01)  # a second sender arrives while the first is starting

    broker = CountingBroker(await_inplace=True)

    @broker.task(task_name=TASK_NAME)
    async def execute_run(run_id: str) -> None: ...

    queue = TaskiqRunQueue(broker)
    await asyncio.gather(queue.enqueue(UUID(int=1)), queue.enqueue(UUID(int=2)))
    await queue.enqueue(UUID(int=3))
    assert broker.starts == 1
