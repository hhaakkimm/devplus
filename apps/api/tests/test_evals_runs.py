import re
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import TypeAdapter
from sqlalchemy import func, select

from app.core.config import Settings
from app.modules.evals import pricing
from app.modules.evals.estimate import estimate_run_cost
from app.modules.evals.graders import ExactGrader, GraderConfig, LlmJudgeGrader, RubricSection
from app.modules.evals.llm import FakeLLMClient
from app.modules.evals.models import Run, RunResult
from app.modules.evals.schemas import CaseIn, VersionOut
from app.modules.evals.service import DatasetService, PromptService, RunService

V = {"system": "s", "user_template": "Say {{name}}", "model": "claude-haiku-5-5"}
EXACT = [{"type": "exact"}]
JUDGE = {
    "type": "llm_judge",
    "rubric": [{"name": "Тон", "description": "Вежливо ли отвечено"}],
    "model": "claude-haiku-5-5",
}
OVER_LIMIT = re.compile(r"^Ожидаемая стоимость \$\d+\.\d{2} превышает лимит \$\d+\.\d{2}$")


@pytest.fixture
def settings(settings: Settings) -> Settings:
    # the shared fixture allows alice and bob only, and a third user is needed here
    return settings.model_copy(update={"allowed_github_logins": "alice, bob, carol"})


async def make_prompt(client, version=V, shared=False):
    r = await client.post("/api/evals/prompts", json={"name": "P", "version": version})
    assert r.status_code == 201, r.text
    p = r.json()
    if shared:
        await client.patch(f"/api/evals/prompts/{p['id']}", json={"shared": True})
    return p


async def make_dataset(client, cases=({"name": "a"}, {"name": "b"}), expected="x"):
    r = await client.post("/api/evals/datasets", json={"name": "D"})
    assert r.status_code == 201, r.text
    ds = r.json()
    for variables in cases:
        r = await client.post(
            f"/api/evals/datasets/{ds['id']}/cases",
            json={"variables": variables, "expected": expected},
        )
        assert r.status_code == 201, r.text
    return ds


def body(prompt, ds, graders=EXACT, **extra):
    return {
        "prompt_version_id": prompt["versions"][-1]["id"],
        "dataset_id": ds["id"],
        "graders": graders,
        **extra,
    }


async def start_run(client, prompt, ds, **kwargs):
    r = await client.post("/api/evals/runs", json=body(prompt, ds, **kwargs))
    assert r.status_code == 201, r.text
    return r.json()


async def test_requires_session(client):
    assert (await client.get("/api/evals/runs?prompt_id=" + "0" * 32)).status_code == 401


async def test_create_snapshots_cases_and_enqueues(client, sign_in, queue, db_session):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    run = await start_run(client, prompt, ds)
    assert (run["source"], run["status"], run["cases_total"], run["cases_done"]) == (
        "lab",
        "queued",
        2,
        0,
    )
    assert (run["prompt_version_id"], run["dataset_id"]) == (
        prompt["versions"][0]["id"],
        ds["id"],
    )
    assert Decimal(run["cost_limit_usd"]) == 5  # the global limit when the request sets none
    assert Decimal(run["estimated_cost_usd"]) > 0
    assert Decimal(run["cost_usd"]) == 0
    assert run["results"] is None
    assert queue.ids == [UUID(run["id"])]
    row = await db_session.get(Run, UUID(run["id"]))
    assert row.graders == [{"type": "exact", "ignore_case": False}]
    assert row.cases == [
        {"position": 1, "variables": {"name": "a"}, "expected": "x"},
        {"position": 2, "variables": {"name": "b"}, "expected": "x"},
    ]


async def test_stored_graders_validate_again(client, sign_in, db_session):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    graders = [
        {"type": "regex", "pattern": "^x", "must_match": False},
        {"type": "json_schema", "schema": {"type": "object"}},
        JUDGE,
    ]
    run = await start_run(client, prompt, ds, graders=graders)
    row = await db_session.get(Run, UUID(run["id"]))
    adapter = TypeAdapter(GraderConfig)
    stored = [adapter.validate_python(g) for g in row.graders]
    assert [g.type for g in stored] == ["regex", "json_schema", "llm_judge"]
    assert stored[1].schema_ == {"type": "object"}  # dumped under its alias "schema"


async def test_estimate_has_no_side_effects(client, sign_in, queue, db_session):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    r = await client.post("/api/evals/runs/estimate", json=body(prompt, ds))
    assert r.status_code == 200
    out = r.json()
    assert Decimal(out["estimated_cost_usd"]) > 0
    assert Decimal(out["cost_limit_usd"]) == 5
    assert await db_session.scalar(select(func.count()).select_from(Run)) == 0
    assert queue.ids == []


async def test_estimate_reports_the_requested_limit(client, sign_in):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    r = await client.post("/api/evals/runs/estimate", json=body(prompt, ds, cost_limit_usd=0.5))
    assert Decimal(r.json()["cost_limit_usd"]) == Decimal("0.5")


async def test_over_limit_is_400(client, sign_in, queue, db_session):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    r = await client.post("/api/evals/runs", json=body(prompt, ds, cost_limit_usd=0.000001))
    assert r.status_code == 400
    assert r.json()["detail"].startswith("Ожидаемая стоимость $")
    assert OVER_LIMIT.match(r.json()["detail"])
    assert await db_session.scalar(select(func.count()).select_from(Run)) == 0
    assert queue.ids == []


async def test_over_limit_message_has_two_decimals(client, sign_in):
    await sign_in("alice")
    prompt = await make_prompt(client, V | {"model": "claude-opus-5-5", "max_tokens": 16000})
    ds = await make_dataset(client, cases=[{"name": "x" * 1000}] * 20, expected="y" * 20_000)
    r = await client.post("/api/evals/runs", json=body(prompt, ds, cost_limit_usd=0.01))
    assert r.status_code == 400
    assert re.fullmatch(
        r"Ожидаемая стоимость \$\d+\.\d{2} превышает лимит \$0\.01", r.json()["detail"]
    )


async def test_limit_above_global_is_422(client, sign_in, queue):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    r = await client.post("/api/evals/runs", json=body(prompt, ds, cost_limit_usd=6))
    assert r.status_code == 422
    assert r.json()["detail"] == "Лимит прогона не больше $5.00"
    assert queue.ids == []


@pytest.mark.parametrize("limit", [0, -1, "NaN", "Infinity"])
async def test_nonsense_limit_is_422(client, sign_in, limit):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    r = await client.post("/api/evals/runs", json=body(prompt, ds, cost_limit_usd=limit))
    assert r.status_code == 422


async def test_empty_dataset_is_422(client, sign_in):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client, cases=[])
    r = await client.post("/api/evals/runs", json=body(prompt, ds))
    assert (r.status_code, r.json()["detail"]) == (422, "В датасете нет кейсов")


async def test_missing_variables_lists_positions(client, sign_in, queue):
    await sign_in("alice")
    prompt = await make_prompt(client)
    ds = await make_dataset(
        client,
        cases=[{"name": "a"}, {"other": "b"}, {"name": "c"}, {"name": "d"}, {"x": "e"}],
    )
    r = await client.post("/api/evals/runs", json=body(prompt, ds))
    assert (r.status_code, r.json()["detail"]) == (
        422,
        "Кейсам 2, 5 не хватает переменных: name",
    )
    assert queue.ids == []


async def test_missing_variables_are_listed_once_and_sorted(client, sign_in):
    await sign_in("alice")
    prompt = await make_prompt(client, V | {"user_template": "{{b}} {{a}} {{c}}"})
    ds = await make_dataset(client, cases=[{"c": "1"}, {"a": "1", "b": "2", "c": "3"}, {}])
    r = await client.post("/api/evals/runs/estimate", json=body(prompt, ds))
    assert r.json()["detail"] == "Кейсам 1, 3 не хватает переменных: a, b, c"


@pytest.mark.parametrize("graders", [[EXACT[0]] * 6, [{"type": "nope"}]])
async def test_graders_are_validated(client, sign_in, graders):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    r = await client.post("/api/evals/runs", json=body(prompt, ds, graders=graders))
    assert r.status_code == 422


async def test_grader_with_nul_is_422(client, sign_in):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    judge = JUDGE | {"rubric": [{"name": "a", "description": "x\x00y"}]}
    r = await client.post("/api/evals/runs", json=body(prompt, ds, graders=[judge]))
    assert r.status_code == 422


async def test_run_visibility(client, sign_in):
    await sign_in("alice")
    prompt = await make_prompt(client, shared=True)
    alice_ds = await make_dataset(client)
    alice_run = await start_run(client, prompt, alice_ds)
    await sign_in("bob")
    bob_run = await start_run(client, prompt, await make_dataset(client))
    runs, listing = "/api/evals/runs", f"/api/evals/runs?prompt_id={prompt['id']}"

    assert (await client.get(f"{runs}/{bob_run['id']}")).status_code == 200  # who started it
    assert (await client.get(f"{runs}/{alice_run['id']}")).status_code == 404  # someone else's
    assert [r["id"] for r in (await client.get(listing)).json()] == [bob_run["id"]]

    await sign_in("alice")  # the prompt author sees every run on the prompt
    assert (await client.get(f"{runs}/{bob_run['id']}")).status_code == 200
    assert {r["id"] for r in (await client.get(listing)).json()} == {
        alice_run["id"],
        bob_run["id"],
    }

    await sign_in("carol")
    assert (await client.get(f"{runs}/{bob_run['id']}")).status_code == 404
    assert (await client.get(listing)).json() == []  # a shared prompt, but none of her runs


async def test_run_on_private_prompt_or_dataset_is_404(client, sign_in, queue):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    await sign_in("bob")
    mine = await make_dataset(client)
    for payload in (body(prompt, mine), body(await make_prompt(client), ds)):
        for url in ("/api/evals/runs", "/api/evals/runs/estimate"):
            assert (await client.post(url, json=payload)).status_code == 404
    assert (await client.get(f"/api/evals/runs?prompt_id={prompt['id']}")).status_code == 404
    assert queue.ids == []


async def test_unknown_run_is_404(client, sign_in):
    await sign_in("alice")
    r = await client.get("/api/evals/runs/00000000-0000-0000-0000-000000000000")
    assert (r.status_code, r.json()) == (404, {"detail": "Не найдено"})


async def test_dataset_replaced_after_create_uses_snapshot(client, sign_in, db_session):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    run = await start_run(client, prompt, ds)
    r = await client.put(
        f"/api/evals/datasets/{ds['id']}/cases",
        content='{"variables": {"name": "new"}}\n',
        headers={"Content-Type": "application/x-ndjson"},
    )
    assert r.status_code == 200
    row = await db_session.get(Run, UUID(run["id"]))
    assert row.cases_total == 2
    assert [c["variables"] for c in row.cases] == [{"name": "a"}, {"name": "b"}]
    assert (await client.get(f"/api/evals/runs/{run['id']}")).json()["cases_total"] == 2


async def test_snapshot_positions_are_renumbered(client, sign_in, db_session):
    await sign_in("alice")
    prompt = await make_prompt(client)
    ds = await make_dataset(client, cases=[{"name": "a"}, {"name": "b"}, {"name": "c"}])
    middle = (await client.get(f"/api/evals/datasets/{ds['id']}")).json()["cases"][1]
    await client.delete(f"/api/evals/datasets/{ds['id']}/cases/{middle['id']}")  # leaves 1, 3
    run = await start_run(client, prompt, ds)
    row = await db_session.get(Run, UUID(run["id"]))
    assert [(c["position"], c["variables"]["name"]) for c in row.cases] == [(1, "a"), (2, "c")]


async def test_get_returns_results_and_latency(client, sign_in, db_session):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    run = await start_run(client, prompt, ds)
    for position, latency, error in [(1, 10, None), (2, 30, None), (3, 20, None), (4, 0, "boom")]:
        db_session.add(
            RunResult(
                run_id=UUID(run["id"]),
                position=position,
                input_vars={"name": "a"},
                output="out",
                truncated=False,
                grades=[{"type": "exact", "score": 1.0, "passed": True}],
                score=1,
                passed=True,
                input_tokens=1,
                output_tokens=1,
                cache_read_tokens=0,
                cost_usd=Decimal("0.001"),
                latency_ms=latency,
                error=error,
            )
        )
    await db_session.flush()
    got = (await client.get(f"/api/evals/runs/{run['id']}")).json()
    # errored cases carry no real latency, so they stay out of the percentiles
    assert (got["latency_p50_ms"], got["latency_p95_ms"]) == (20, 29)
    first = got["results"][0]
    assert [r["position"] for r in got["results"]] == [1, 2, 3, 4]
    assert first == {
        "position": 1,
        "input_vars": {"name": "a"},
        "output": "out",
        "truncated": False,
        "grades": [{"type": "exact", "score": 1.0, "passed": True}],
        "score": 1.0,
        "passed": True,
        "cost_usd": "0.001",
        "latency_ms": 10,
    }
    assert got["results"][3]["error"] == "boom"


async def test_trainer_run_exposes_only_scores(
    client, sign_in, db_session, settings, fake_llm, queue
):
    alice = await sign_in("alice")
    prompt = await make_prompt(client)
    service = RunService(
        db_session,
        settings,
        fake_llm,
        queue,
        PromptService(db_session),
        DatasetService(db_session),
    )
    secret = CaseIn(variables={"name": "hidden-input"}, expected="hidden-answer")
    out = await service.create_for(
        alice.id,
        UUID(prompt["versions"][0]["id"]),
        [secret],
        [ExactGrader(type="exact")],
        "trainer",
        task_slug="start/iso-dates",
    )
    assert (out.source, out.cases_total, out.dataset_id) == ("trainer", 1, None)
    assert queue.ids == [out.id]
    db_session.add(
        RunResult(
            run_id=out.id,
            position=1,
            input_vars={"name": "hidden-input"},
            output="hidden-output",
            truncated=False,
            grades=[{"type": "exact"}],
            score=0.5,
            passed=False,
            input_tokens=1,
            output_tokens=1,
            cache_read_tokens=0,
            cost_usd=Decimal("0.001"),
            latency_ms=5,
            error="hidden-error",
        )
    )
    await db_session.flush()

    for url in (f"/api/evals/runs/{out.id}", f"/api/evals/runs?prompt_id={prompt['id']}"):
        r = await client.get(url)
        assert r.status_code == 200
        assert not re.search(r"hidden|input_vars|output|grades|cases\"|expected", r.text), r.text
    got = (await client.get(f"/api/evals/runs/{out.id}")).json()
    assert got["results"] == [{"position": 1, "score": 0.5, "passed": False}]


async def test_enqueue_failure_fails_the_run(client, sign_in, db_session, settings, fake_llm):
    alice = await sign_in("alice")
    prompt = await make_prompt(client)

    class BrokenQueue:
        async def enqueue(self, run_id: UUID) -> None:
            raise ConnectionError("redis is down")

    service = RunService(
        db_session,
        settings,
        fake_llm,
        BrokenQueue(),
        PromptService(db_session),
        DatasetService(db_session),
    )
    with pytest.raises(ConnectionError):
        await service.create_for(
            alice.id,
            UUID(prompt["versions"][0]["id"]),
            [CaseIn(variables={"name": "a"})],
            [],
            "review",
        )
    # a run that never reached the queue must not wait there to be billed later
    [run] = (await db_session.scalars(select(Run))).all()
    assert (run.status, run.error) == ("failed", "Не удалось поставить в очередь")


def version(**kwargs) -> VersionOut:
    fields = {
        "id": UUID(int=1),
        "number": 1,
        "system": "s" * 40,
        "user_template": "{{x}}",
        "model": "claude-haiku-5-5",
        "effort": "medium",
        "max_tokens": 1024,
        "output_schema": None,
        "created_at": "2026-10-26T00:00:00Z",
    }
    return VersionOut.model_validate(fields | kwargs)


async def test_estimate_math():
    # FakeLLMClient counts len // 4: the first case is 40 + 60 chars = 25 tokens, 0.25 per char
    cases = [
        CaseIn(variables={"x": "a" * 60}, expected="e" * 40),  # answer: 40 chars = 10 tokens
        CaseIn(variables={"x": "b" * 120}),  # no reference: 300 tokens; input 160 chars = 40
    ]
    llm = FakeLLMClient()
    got = await estimate_run_cost(llm, version(), cases, [])
    assert got == pricing.cost_usd("claude-haiku-5-5", 25, 10) + pricing.cost_usd(
        "claude-haiku-5-5", 40, 300
    )
    assert len(llm.calls) == 0  # token counting is not a completion


async def test_estimate_adds_the_judge():
    case = CaseIn(variables={"x": "a" * 60}, expected="e" * 40)
    judge = LlmJudgeGrader(
        type="llm_judge",
        rubric=[RubricSection(name="n" * 10, description="d" * 30)],
        model="claude-sonnet-5-5",
    )
    base = await estimate_run_cost(FakeLLMClient(), version(), [case], [])
    got = await estimate_run_cost(FakeLLMClient(), version(), [case], [judge])
    # judge input: 500 overhead, case (60 chars) and rubric (40 chars) at 0.25, 10-token answer
    judge_in = 500 + 25 + 10
    assert got - base == pricing.cost_usd("claude-sonnet-5-5", judge_in, 400)


async def test_estimate_caps_the_answer_at_max_tokens():
    case = CaseIn(variables={"x": "a" * 60})  # no reference: 300 tokens, capped at 64
    got = await estimate_run_cost(FakeLLMClient(), version(max_tokens=64), [case], [])
    assert got == pricing.cost_usd("claude-haiku-5-5", 25, 64)
