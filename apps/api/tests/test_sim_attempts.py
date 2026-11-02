import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import anthropic
import httpx
import pytest
from sqlalchemy import func, select

from app.modules.evals.judge import (
    JUDGE_MAX_TOKENS,
    JUDGE_SYSTEM,
    judge,
    judge_request,
    judge_schema,
    judge_user,
)
from app.modules.evals.llm import LLMError
from app.modules.evals.service import LlmJudgeGrader, RubricSection, cost_usd
from app.modules.simulator import review, service
from app.modules.simulator.engine.graph import Graph, structural_errors
from app.modules.simulator.engine.lint import lint
from app.modules.simulator.engine.scenarios import run_scenario
from app.modules.simulator.models import SimAttempt
from app.modules.simulator.review import graph_text, review_request
from app.modules.simulator.schemas import SimAnswers, SimGraph
from app.modules.simulator.tasks import load_sim_tasks

REAL = Path(__file__).parents[3] / "content"
BASE = "/api/simulator"
TASK = f"{BASE}/tasks/system-design/url-shortener"
ATTEMPTS = f"{TASK}/attempts"
KEY = "system-design/url-shortener"
SIM_TASK = next(t for t in load_sim_tasks(REAL) if t.slug == "url-shortener")
HIDDEN = [s for s in SIM_TASK.scenarios if not s.visible]
RUBRIC = [s.name for s in SIM_TASK.review.rubric]
GOOD = SIM_TASK.reference_graph.model_dump()
USER = {"id": "user", "type": "User"}
NAIVE = {
    "nodes": [USER, {"id": "server", "type": "Server"}, {"id": "db", "type": "Database"}],
    "edges": [{"source": "user", "target": "server"}, {"source": "server", "target": "db"}],
}
ANSWERS = {
    "requirements": "ОТВЕТ-ТРЕБОВАНИЯ: создать ссылку и быстро по ней перейти",
    "estimates": "ОТВЕТ-ОЦЕНКА: 19 000 переходов в секунду",
    "tradeoffs": "ОТВЕТ-КОМПРОМИССЫ: 302 ради аналитики",
}
UNAVAILABLE = "AI-разбор не удался: Claude API недоступен"
LIMIT = "Лимит отправок на сегодня исчерпан"


def body(graph=GOOD, answers=ANSWERS) -> dict:
    return {"graph": graph, "answers": answers}


def numbers(value) -> set[float]:
    """Every number in a parsed JSON document."""
    if isinstance(value, bool):
        return set()
    if isinstance(value, int | float):
        return {value}
    if isinstance(value, list):
        return set().union(*map(numbers, value)) if value else set()
    if isinstance(value, dict):
        return set().union(*map(numbers, value.values())) if value else set()
    return set()


def judge_prompt(b: dict) -> str:
    """The judge's prompt for this submission, built the way the service builds it."""
    g = SimGraph.model_validate(b["graph"])
    scale = SIM_TASK.scale
    results = [run_scenario(g, scale.peak_rps, scale.read_ratio, s) for s in SIM_TASK.scenarios]
    findings = lint(g, scale.read_ratio)
    _, req, _, _ = review_request(SIM_TASK, g, results, findings, SimAnswers(**b["answers"]))
    return req.user


def script(fake_llm, b: dict, score: int = 5, names: list[str] = RUBRIC) -> None:
    """The judge's answer to exactly this submission; sections come back in reverse order."""
    answer = {
        "sections": [{"name": n, "score": score, "reason": f"r-{n}"} for n in reversed(names)],
        "comment": "итог",
    }
    fake_llm.responses = {
        **(fake_llm.responses or {}),
        judge_prompt(b): json.dumps(answer, ensure_ascii=False),
    }


async def add_rows(db_session, user, n, *, age=timedelta(minutes=1), error=None, key=KEY):
    for _ in range(n):
        db_session.add(
            SimAttempt(
                user_id=user.id,
                task_key=key,
                graph=GOOD,
                answers=ANSWERS,
                scenarios=[],
                findings=[],
                review=None,
                review_error=error,
                score=None,
                passed=False,
                cost_usd=Decimal(0),
                created_at=datetime.now(UTC) - age,
            )
        )
    await db_session.commit()


async def stored(db_session) -> int:
    return await db_session.scalar(select(func.count()).select_from(SimAttempt))


def solved(tasks: list[dict]) -> dict[str, bool]:
    return {t["slug"]: t["solved"] for t in tasks}


async def test_submit_passes_with_reference_graph_and_good_review(
    client, sign_in, fake_llm, db_session
):
    await sign_in()
    script(fake_llm, body())
    res = await client.post(ATTEMPTS, json=body())
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["passed"] is True
    assert data["score"] >= SIM_TASK.review.threshold
    assert data["review_error"] is None
    assert [s["id"] for s in data["scenarios"]] == [s.id for s in SIM_TASK.scenarios]
    assert all(s["passed"] for s in data["scenarios"])
    assert data["findings"] == []
    assert data["review"] == {
        "score": data["score"],
        "passed": True,
        # in the order of the rubric, whatever order the judge used
        "sections": [{"name": n, "score": 5, "comment": f"r-{n}"} for n in RUBRIC],
        "comment": "итог",
    }
    assert Decimal(data["cost_usd"]) > 0
    assert data["answers"] == ANSWERS
    assert SimGraph.model_validate(data["graph"]) == SimGraph.model_validate(GOOD)

    # the judge saw the task, the scheme, every scenario, the reference and the three answers
    [req] = fake_llm.calls
    assert (req.model, req.effort) == ("claude-sonnet-5-5", "medium")
    assert SIM_TASK.statement.splitlines()[0] in req.user
    assert graph_text(SimGraph.model_validate(GOOD)) in req.user
    assert all(s.title in req.user for s in SIM_TASK.scenarios)
    assert SIM_TASK.review.reference.strip() in req.user
    assert "Требования и допущения:\n" + ANSWERS["requirements"] in req.user
    assert "Оценка нагрузки:\n" + ANSWERS["estimates"] in req.user
    assert "Ключевые решения и компромиссы:\n" + ANSWERS["tradeoffs"] in req.user

    tasks = (await client.get(f"{BASE}/tasks")).json()
    assert solved(tasks) == {"url-shortener": True, "chat": False, "news-feed": False}
    assert (await client.get(ATTEMPTS)).json() == [data]
    row = await db_session.get(SimAttempt, UUID(data["id"]))
    assert (row.task_key, row.passed, row.cost_usd) == (KEY, True, Decimal(data["cost_usd"]))


async def test_submit_fails_on_critical_finding(client, sign_in, fake_llm):
    await sign_in()
    # the database is open to users, but the edge carries nothing: every scenario still passes
    exposed = {**GOOD, "edges": [*GOOD["edges"], {"source": "user", "target": "db", "ratio": 0}]}
    script(fake_llm, body(exposed))
    res = await client.post(ATTEMPTS, json=body(exposed))
    assert res.status_code == 201, res.text
    data = res.json()
    assert all(s["passed"] for s in data["scenarios"])
    assert [f["code"] for f in data["findings"] if f["severity"] == "critical"] == [
        "STORAGE_EXPOSED"
    ]
    assert data["review"]["passed"] is True
    assert data["passed"] is False
    assert solved((await client.get(f"{BASE}/tasks")).json())["url-shortener"] is False


async def test_submit_fails_on_failed_scenario(client, sign_in, fake_llm):
    await sign_in()
    script(fake_llm, body(NAIVE))
    data = (await client.post(ATTEMPTS, json=body(NAIVE))).json()
    assert data["review"]["passed"] is True
    assert not all(s["passed"] for s in data["scenarios"])
    assert data["passed"] is False


async def test_structural_errors_422_and_no_claude_call(client, sign_in, fake_llm, db_session):
    await sign_in()
    # a dead-end server plus two nodes nobody reaches: three errors in one message
    broken = {
        "nodes": [
            USER,
            {"id": "server", "type": "Server"},
            {"id": "a", "type": "Server"},
            {"id": "b", "type": "Database"},
        ],
        "edges": [{"source": "user", "target": "server"}, {"source": "a", "target": "b"}],
    }
    errors = structural_errors(Graph.model_validate(broken))
    assert len(errors) == 3
    for graph, detail in (
        (broken, "Схема не прогоняется: " + "; ".join(errors)),
        ({"nodes": [], "edges": []}, "Схема не прогоняется: Нужен ровно один узел User"),
    ):
        res = await client.post(ATTEMPTS, json=body(graph))
        assert res.status_code == 422
        assert res.json() == {"detail": detail}
    assert fake_llm.calls == []
    assert await stored(db_session) == 0


@pytest.mark.parametrize(
    "answers",
    [
        {**ANSWERS, "estimates": "x" * 5001},
        {**ANSWERS, "tradeoffs": "a\x00b"},
        {"requirements": "r", "estimates": "e"},
    ],
    ids=["too-long", "nul", "missing"],
)
async def test_answers_validation_422(client, sign_in, fake_llm, answers):
    await sign_in()
    assert (await client.post(ATTEMPTS, json=body(answers=answers))).status_code == 422
    assert fake_llm.calls == []


async def test_answers_at_the_limit_are_accepted(client, sign_in, fake_llm):
    await sign_in()
    full = dict.fromkeys(ANSWERS, "я" * 5000)
    assert (await client.post(ATTEMPTS, json=body(answers=full))).status_code == 201


def _api_error() -> Exception:
    return anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))


@pytest.mark.parametrize(
    ("method", "failure"),
    [
        ("complete", "api"),
        ("complete", "cli"),
        ("complete", "hang"),
        ("count_tokens", "api"),
    ],
)
async def test_review_api_error_saved_with_review_error(
    client, sign_in, fake_llm, db_session, monkeypatch, caplog, method, failure
):
    user = await sign_in()
    await add_rows(db_session, user, 19)  # one send left today
    original = getattr(fake_llm, method)

    async def broken(req):
        if failure == "hang":
            await asyncio.sleep(5)
        raise _api_error() if failure == "api" else LLMError("claude exited with 1")

    setattr(fake_llm, method, broken)
    monkeypatch.setattr(service, "JUDGE_TIMEOUT", timedelta(milliseconds=50))
    with caplog.at_level(logging.WARNING, logger=service.logger.name):
        res = await client.post(ATTEMPTS, json=body())
    assert res.status_code == 201, res.text
    data = res.json()
    assert (data["passed"], data["review"], data["score"]) == (False, None, None)
    assert data["review_error"] == UNAVAILABLE
    assert Decimal(data["cost_usd"]) == 0
    assert all(s["passed"] for s in data["scenarios"])  # the simulator's part is kept
    [record] = [r for r in caplog.records if r.name == service.logger.name]
    assert (record.attempt_id, record.task_key) == (data["id"], KEY)
    assert record.exc_info is not None
    assert not any(a in caplog.text for a in ANSWERS.values())
    assert (await client.get(ATTEMPTS)).json()[0] == data

    # not counted: the 19 earlier sends still leave room for one, then the limit
    setattr(fake_llm, method, original)
    script(fake_llm, body())
    assert (await client.post(ATTEMPTS, json=body())).status_code == 201
    assert (await client.post(ATTEMPTS, json=body())).status_code == 429


async def test_judge_bad_answer_saved_with_review_error(
    client, sign_in, fake_llm, db_session, caplog
):
    user = await sign_in()
    script(fake_llm, body(), names=["Чужой раздел"])
    with caplog.at_level(logging.WARNING, logger=service.logger.name):
        res = await client.post(ATTEMPTS, json=body())
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["review_error"] == "AI-разбор не удался: Разделы судьи не совпадают с рубрикой"
    assert (data["passed"], data["review"], data["score"]) == (False, None, None)
    assert Decimal(data["cost_usd"]) > 0  # the judge was paid for even so
    [record] = [r for r in caplog.records if r.name == service.logger.name]
    assert (record.attempt_id, record.task_key) == (data["id"], KEY)
    assert not any(a in caplog.text for a in ANSWERS.values())
    assert solved((await client.get(f"{BASE}/tasks")).json())["url-shortener"] is False
    # a failed review is not charged to the limit
    await add_rows(db_session, user, 19)
    script(fake_llm, body())
    assert (await client.post(ATTEMPTS, json=body())).status_code == 201


NOW = timedelta(minutes=1)
CHAT = "system-design/chat"


@pytest.mark.parametrize(
    ("rows", "status"),
    [
        pytest.param([(20, NOW, None, KEY)], 429, id="20 today"),
        pytest.param([(20, NOW, None, CHAT)], 429, id="other tasks count"),
        pytest.param([(19, NOW, None, KEY), (5, NOW, UNAVAILABLE, KEY)], 201, id="errors are free"),
        pytest.param(
            [(19, NOW, None, KEY), (1, timedelta(hours=25), None, KEY)], 201, id="older is free"
        ),
        pytest.param(
            [(19, NOW, None, KEY), (1, timedelta(hours=23), None, KEY)], 429, id="23h ago counts"
        ),
    ],
)
async def test_daily_limit_429(client, sign_in, fake_llm, db_session, rows, status):
    user = await sign_in()
    for n, age, error, key in rows:
        await add_rows(db_session, user, n, age=age, error=error, key=key)
    before = await stored(db_session)
    script(fake_llm, body())
    res = await client.post(ATTEMPTS, json=body())
    assert res.status_code == status, res.text
    if status == 429:
        assert res.json() == {"detail": LIMIT}
        assert fake_llm.calls == []
        assert await stored(db_session) == before
        await sign_in("bob")  # the limit is per user
        assert (await client.post(ATTEMPTS, json=body())).status_code == 201
    else:
        # that was the 20th send of the day: the next one is over the limit
        assert (await client.post(ATTEMPTS, json=body())).json() == {"detail": LIMIT}
        assert len(fake_llm.calls) == 1


async def test_review_cost_over_limit_400(client, sign_in, fake_llm, db_session):
    await sign_in()

    async def huge(req):
        return 1_000_000

    fake_llm.count_tokens = huge
    res = await client.post(ATTEMPTS, json=body())
    assert res.status_code == 400
    expected = cost_usd("claude-sonnet-5-5", 1_000_000, review.REVIEW_OUTPUT_TOKENS)
    assert expected > Decimal("0.10")
    assert res.json() == {
        "detail": f"Ожидаемая стоимость разбора ${expected:.2f} выше лимита $0.10"
    }
    assert fake_llm.calls == []
    assert await stored(db_session) == 0


async def test_attempt_hides_hidden_numbers(client, sign_in, fake_llm):
    await sign_in()
    responses = []
    # the reference passes everything, the naive scheme fails the hidden scenarios too
    for graph in (GOOD, NAIVE):
        script(fake_llm, body(graph))
        responses.append(await client.post(ATTEMPTS, json=body(graph)))
    responses.append(await client.get(ATTEMPTS))
    attempts = [r.json() for r in responses[:2]] + responses[2].json()
    assert len(attempts) == 4
    reference_lines = [line for line in SIM_TASK.review.reference.splitlines() if line]
    rubric_texts = [s.description for s in SIM_TASK.review.rubric]
    for res in responses:
        assert res.status_code in (200, 201), res.text
        body_text = res.text
        for secret in (
            "reference",
            "rubric",
            "threshold",
            "max_latency_ms",
            "max_error_rate",
            "max_message_loss",
            "multiplier",
            "duration_s",
            "failure",
            *reference_lines,
            *rubric_texts,
        ):
            assert secret not in body_text
    # hidden targets as numbers: 0.9 is a substring of 0.95, so JSON values are compared
    targets = {v for s in HIDDEN for v in (s.max_latency_ms, s.max_error_rate, s.multiplier)}
    targets -= {1}  # a multiplier of 1 is no secret, and a score of 1.0 equals it
    for attempt in attempts:
        shown = numbers({k: v for k, v in attempt.items() if k != "graph"})
        assert not shown & targets
        verdicts = attempt["scenarios"]
        assert all(set(v) == {"id", "title", "visible", "passed", "explanation"} for v in verdicts)
        # after a submission the hidden scenarios are named, with a verdict and no target
        hidden = [v for v in verdicts if not v["visible"]]
        assert [v["title"] for v in hidden] == [s.title for s in HIDDEN]
        assert all("цел" not in v["explanation"] for v in hidden)
    naive_hidden = [v for v in attempts[1]["scenarios"] if not v["visible"]]
    assert not all(v["passed"] for v in naive_hidden)


async def test_attempts_private(client, sign_in, fake_llm):
    await sign_in("alice")
    script(fake_llm, body())
    assert (await client.post(ATTEMPTS, json=body())).status_code == 201
    assert len((await client.get(ATTEMPTS)).json()) == 1
    await sign_in("bob")
    assert (await client.get(ATTEMPTS)).json() == []
    assert solved((await client.get(f"{BASE}/tasks")).json())["url-shortener"] is False


async def test_attempts_newest_first_and_per_task(client, sign_in, db_session):
    user = await sign_in()
    await add_rows(db_session, user, 1, age=timedelta(hours=2))
    await add_rows(db_session, user, 1, age=timedelta(hours=1), error=UNAVAILABLE)
    await add_rows(db_session, user, 1, age=timedelta(hours=3), key=CHAT)
    got = (await client.get(ATTEMPTS)).json()
    assert [a["review_error"] for a in got] == [UNAVAILABLE, None]
    assert got[0]["created_at"] > got[1]["created_at"]


async def test_attempts_unknown_task_and_auth(client, sign_in):
    for method, path in (("get", ATTEMPTS), ("post", ATTEMPTS)):
        res = await getattr(client, method)(path, **({"json": body()} if method == "post" else {}))
        assert res.status_code == 401
    await sign_in()
    for path in ("system-design/nope", "nope/url-shortener"):
        url = f"{BASE}/tasks/{path}/attempts"
        assert (await client.get(url)).status_code == 404
        assert (await client.post(url, json=body())).status_code == 404


def test_graph_text():
    g = Graph.model_validate(
        {
            "nodes": [
                USER,
                {"id": "api", "type": "Server", "params": {"replicas": 2}},
                {"id": "cache", "type": "Cache"},
                {"id": "q", "type": "Queue"},
                {"id": "spare", "type": "Worker"},
            ],
            "edges": [
                {"source": "user", "target": "api"},
                {"source": "api", "target": "cache", "ratio": 0.5},
                {"source": "api", "target": "q"},  # made async by the graph
            ],
        }
    )
    assert graph_text(g).splitlines() == [
        "User user → Server api (Копий: 2) [sync ×1]",
        "Server api (Копий: 2) → Cache cache (Доля попаданий: 0.8, Копий: 1) [sync ×0.5]",
        "Server api (Копий: 2) → Queue q (Размер очереди: 100000) [async ×1]",
        "Worker spare (Копий: 1): без связей",
    ]


async def test_judge_unchanged(fake_llm):
    """`judge` sends exactly `judge_request`, with the evaluator's model, effort and limits."""
    cfg = LlmJudgeGrader(type="llm_judge", rubric=[RubricSection(name="A", description="полнота")])
    inputs = {"Вопрос": "2+2"}
    await judge(fake_llm, cfg, inputs, "4", "ответ")
    await judge(fake_llm, cfg, inputs, "4", "ответ", system="СИСТЕМА")
    assert fake_llm.calls == [
        judge_request(cfg, inputs, "4", "ответ"),
        judge_request(cfg, inputs, "4", "ответ", system="СИСТЕМА"),
    ]
    req = fake_llm.calls[0]
    assert (req.model, req.system, req.effort, req.max_tokens, req.allow_fallback) == (
        "claude-sonnet-5-5",
        JUDGE_SYSTEM,
        "medium",
        JUDGE_MAX_TOKENS,
        True,
    )
    assert req.user == judge_user(cfg, inputs, "4", "ответ")
    assert req.output_schema == judge_schema(cfg.rubric)
