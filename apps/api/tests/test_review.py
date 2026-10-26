import dataclasses
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import anthropic
import httpx
import pytest

from app.modules.evals.llm import CompletionRequest
from app.modules.review.critic import CRITIC_SCHEMA, CRITIC_SYSTEM, critic_user

SYSTEM = "Ты помощник."
TEMPLATE = "Ответь на вопрос: {{question}}"
VERSION = {"system": SYSTEM, "user_template": TEMPLATE, "model": "claude-haiku-5-5"}
EXACT = [{"type": "exact"}]
VARIABLES_CHANGED = (
    "Переписанная версия использует другие переменные — на текущих датасетах она не запустится"
)


async def make_prompt(client, shared=False, version=VERSION):
    r = await client.post("/api/evals/prompts", json={"name": "P", "version": version})
    assert r.status_code == 201, r.text
    prompt = r.json()
    if shared:
        await client.patch(f"/api/evals/prompts/{prompt['id']}", json={"shared": True})
    return prompt


async def make_dataset(client):
    ds = (await client.post("/api/evals/datasets", json={"name": "D"})).json()
    for question in ("a", "b"):
        r = await client.post(
            f"/api/evals/datasets/{ds['id']}/cases",
            json={"variables": {"question": question}, "expected": "x"},
        )
        assert r.status_code == 201, r.text
    return ds


async def review_version(client, version):
    r = await client.post("/api/review", json={"prompt_version_id": version["id"]})
    assert r.status_code == 201, r.text
    return r.json()


async def check(client, review, ds):
    return await client.post(
        f"/api/review/{review['id']}/check", json={"dataset_id": ds["id"], "graders": EXACT}
    )


async def versions_of(client, prompt_id):
    return (await client.get(f"/api/evals/prompts/{prompt_id}")).json()["versions"]


async def test_requires_session(client):
    assert (await client.post("/api/review", json={"system": "x"})).status_code == 401
    assert (await client.get(f"/api/review/{uuid4()}")).status_code == 401


async def test_free_text_review_creates_prompt_v1_v2(client, sign_in, fake_llm_critic, fake_llm):
    await sign_in("alice")
    answer = fake_llm_critic(SYSTEM, TEMPLATE)
    r = await client.post("/api/review", json={"system": SYSTEM, "user_template": TEMPLATE})
    assert r.status_code == 201, r.text
    review = r.json()
    assert review["sections"] == answer["sections"]
    assert review["issues"] == answer["issues"]
    assert review["rewritten"] == answer["rewritten"]
    assert review["variables_changed"] is False
    assert Decimal(review["cost_usd"]) == Decimal("0.0014")  # 100 in and 50 out on Opus 5.5

    prompt = (await client.get(f"/api/evals/prompts/{review['prompt_id']}")).json()
    assert prompt["name"] == f"Ревью от {datetime.now(UTC).date().isoformat()}"
    v1, v2 = prompt["versions"]
    assert (v1["number"], v1["system"], v1["user_template"]) == (1, SYSTEM, TEMPLATE)
    assert (v2["number"], v2["system"], v2["user_template"]) == (
        2,
        answer["rewritten"]["system"],
        TEMPLATE,
    )
    for v in (v1, v2):
        assert (v["model"], v["effort"], v["max_tokens"]) == ("claude-sonnet-5-5", "medium", 1024)
    assert (review["prompt_version_id"], review["rewritten_version_id"]) == (v1["id"], v2["id"])
    assert (await client.get(f"/api/review/{review['id']}")).json() == review
    assert fake_llm.calls == [
        CompletionRequest(
            "claude-opus-5-5",
            CRITIC_SYSTEM,
            user=critic_user(SYSTEM, TEMPLATE),
            effort="high",
            max_tokens=8000,
            output_schema=CRITIC_SCHEMA,
            allow_fallback=True,
        )
    ]


async def test_review_of_own_version_check_adds_version(client, sign_in, fake_llm_critic, queue):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    answer = fake_llm_critic(SYSTEM, TEMPLATE)
    review = await review_version(client, prompt["versions"][0])
    assert review["prompt_id"] == prompt["id"]
    assert review["prompt_version_id"] == prompt["versions"][0]["id"]
    assert review["rewritten_version_id"] is None
    assert len(await versions_of(client, prompt["id"])) == 1  # nothing is added before the check

    r = await check(client, review, ds)
    assert r.status_code == 201, r.text
    run_a, run_b = r.json()["run_a"], r.json()["run_b"]
    assert (run_a["source"], run_b["source"]) == ("review", "review")
    v1, v2 = await versions_of(client, prompt["id"])
    assert (v1["number"], v2["number"]) == (1, 2)
    assert (v2["system"], v2["user_template"]) == (answer["rewritten"]["system"], TEMPLATE)
    assert (v2["model"], v2["max_tokens"]) == ("claude-haiku-5-5", 1024)  # the settings carry over
    assert (run_a["prompt_version_id"], run_b["prompt_version_id"]) == (v1["id"], v2["id"])
    assert queue.ids == [UUID(run_a["id"]), UUID(run_b["id"])]
    assert (await client.get(f"/api/review/{review['id']}")).json()["rewritten_version_id"] == v2[
        "id"
    ]

    # checking again, on another dataset or graders, reuses the rewritten version
    again = (await check(client, review, ds)).json()
    assert again["run_b"]["prompt_version_id"] == v2["id"]
    assert len(await versions_of(client, prompt["id"])) == 2


async def bob_prompts(client):
    return [p for p in (await client.get("/api/evals/prompts")).json() if p["owner_login"] == "bob"]


async def runs_of(client, prompt_id):
    r = await client.get(f"/api/evals/runs?prompt_id={prompt_id}")
    assert r.status_code == 200, r.text
    return r.json()


async def test_review_of_foreign_shared_version_copies_first(
    client, sign_in, fake_llm_critic, queue
):
    await sign_in("alice")
    prompt = await make_prompt(client, shared=True)
    await sign_in("bob")
    ds = await make_dataset(client)
    answer = fake_llm_critic(SYSTEM, TEMPLATE)
    review = await review_version(client, prompt["versions"][0])
    assert review["prompt_id"] == prompt["id"]
    assert len(await versions_of(client, prompt["id"])) == 1  # reviewing copies nothing yet

    r = await check(client, review, ds)
    assert r.status_code == 201, r.text
    run_a, run_b = r.json()["run_a"], r.json()["run_b"]
    mine = await bob_prompts(client)
    assert [p["name"] for p in mine] == ["P (копия)"]
    copy = (await client.get(f"/api/evals/prompts/{mine[0]['id']}")).json()
    v1, v2 = copy["versions"]
    assert [v["number"] for v in copy["versions"]] == [1, 2]
    assert (v1["system"], v1["user_template"]) == (SYSTEM, TEMPLATE)
    assert v2["system"] == answer["rewritten"]["system"]
    # both runs are in the reviewer's copy, in the author's prompt there is nothing
    assert (run_a["prompt_version_id"], run_b["prompt_version_id"]) == (v1["id"], v2["id"])
    assert (run_a["source"], run_b["source"]) == ("review", "review")
    assert queue.ids == [UUID(run_a["id"]), UUID(run_b["id"])]
    assert len(await versions_of(client, prompt["id"])) == 1
    await sign_in("alice")
    assert await runs_of(client, prompt["id"]) == []
    await sign_in("bob")
    assert {r["id"] for r in await runs_of(client, copy["id"])} == {run_a["id"], run_b["id"]}
    # the review now points into the copy
    moved = (await client.get(f"/api/review/{review['id']}")).json()
    assert (moved["prompt_id"], moved["prompt_version_id"]) == (copy["id"], v1["id"])
    assert moved["rewritten_version_id"] == v2["id"]

    # a second check reuses the copy and both of its versions
    again = (await check(client, review, ds)).json()
    assert (again["run_a"]["prompt_version_id"], again["run_b"]["prompt_version_id"]) == (
        v1["id"],
        v2["id"],
    )
    assert len(await bob_prompts(client)) == 1
    assert len(await versions_of(client, copy["id"])) == 2


async def test_review_of_older_foreign_version_adds_it_to_the_copy(
    client, sign_in, fake_llm_critic, queue
):
    await sign_in("alice")
    old = {**VERSION, "effort": "low", "max_tokens": 2048}
    prompt = await make_prompt(client, shared=True, version=old)
    r = await client.post(
        f"/api/evals/prompts/{prompt['id']}/versions",
        json={**VERSION, "system": "Новый системный промпт", "model": "claude-sonnet-5-5"},
    )
    assert r.status_code == 201, r.text
    await sign_in("bob")
    ds = await make_dataset(client)
    answer = fake_llm_critic(SYSTEM, TEMPLATE)
    review = await review_version(client, prompt["versions"][0])  # v1, not the latest

    r = await check(client, review, ds)
    assert r.status_code == 201, r.text
    run_a, run_b = r.json()["run_a"], r.json()["run_b"]
    [mine] = await bob_prompts(client)
    copy = (await client.get(f"/api/evals/prompts/{mine['id']}")).json()
    # the copy holds alice's latest, then the reviewed text, then the rewrite
    latest, reviewed, rewritten = copy["versions"]
    assert [v["number"] for v in copy["versions"]] == [1, 2, 3]
    assert (latest["system"], latest["model"]) == ("Новый системный промпт", "claude-sonnet-5-5")
    assert (reviewed["system"], reviewed["user_template"]) == (SYSTEM, TEMPLATE)
    assert (reviewed["model"], reviewed["effort"], reviewed["max_tokens"]) == (
        "claude-haiku-5-5",
        "low",
        2048,
    )
    assert rewritten["system"] == answer["rewritten"]["system"]
    assert (rewritten["model"], rewritten["effort"], rewritten["max_tokens"]) == (
        "claude-haiku-5-5",
        "low",
        2048,
    )
    assert (run_a["prompt_version_id"], run_b["prompt_version_id"]) == (
        reviewed["id"],
        rewritten["id"],
    )
    assert len(await versions_of(client, prompt["id"])) == 2
    await sign_in("alice")
    assert await runs_of(client, prompt["id"]) == []


async def test_check_on_incompatible_dataset_adds_nothing(client, sign_in, fake_llm_critic, queue):
    await sign_in("alice")
    prompt = await make_prompt(client, shared=True)
    await sign_in("bob")
    ds = (await client.post("/api/evals/datasets", json={"name": "D"})).json()
    await client.post(f"/api/evals/datasets/{ds['id']}/cases", json={"variables": {"other": "x"}})
    fake_llm_critic(SYSTEM, TEMPLATE)
    review = await review_version(client, prompt["versions"][0])

    r = await check(client, review, ds)
    assert r.status_code == 422, r.text
    assert "question" in r.json()["detail"]
    # no copy, no new version and no run: the dataset is refused first
    assert [
        p for p in (await client.get("/api/evals/prompts")).json() if p["owner_login"] == "bob"
    ] == []
    assert len(await versions_of(client, prompt["id"])) == 1
    assert queue.ids == []


async def test_variables_changed_blocks_check(client, sign_in, fake_llm_critic, queue):
    await sign_in("alice")
    prompt, ds = await make_prompt(client), await make_dataset(client)
    fake_llm_critic(SYSTEM, TEMPLATE, rewritten={"user_template": TEMPLATE + " Тон: {{tone}}"})
    review = await review_version(client, prompt["versions"][0])
    assert review["variables_changed"] is True

    r = await check(client, review, ds)
    assert r.status_code == 422
    assert r.json() == {"detail": VARIABLES_CHANGED}
    assert len(await versions_of(client, prompt["id"])) == 1
    assert queue.ids == []


async def test_dropped_variable_counts_as_changed(client, sign_in, fake_llm_critic):
    await sign_in("alice")
    fake_llm_critic(SYSTEM, TEMPLATE, rewritten={"user_template": "Ответь на вопрос."})
    r = await client.post("/api/review", json={"system": SYSTEM, "user_template": TEMPLATE})
    assert r.json()["variables_changed"] is True


async def test_review_is_private(client, sign_in, fake_llm_critic, fake_llm):
    await sign_in("alice")
    prompt = await make_prompt(client)  # not shared
    fake_llm_critic(SYSTEM, TEMPLATE)
    review = await review_version(client, prompt["versions"][0])

    await sign_in("bob")
    ds = await make_dataset(client)
    assert (await client.get(f"/api/review/{review['id']}")).status_code == 404
    assert (await check(client, review, ds)).status_code == 404
    # nor can bob review a version he may not see, and the critic is not paid for it
    calls = len(fake_llm.calls)
    r = await client.post("/api/review", json={"prompt_version_id": prompt["versions"][0]["id"]})
    assert r.status_code == 404
    assert len(fake_llm.calls) == calls


async def test_check_needs_a_dataset_the_user_can_see(client, sign_in, fake_llm_critic):
    await sign_in("alice")
    ds = await make_dataset(client)  # not shared
    await sign_in("bob")
    fake_llm_critic(SYSTEM, TEMPLATE)
    review = (
        await client.post("/api/review", json={"system": SYSTEM, "user_template": TEMPLATE})
    ).json()
    assert (await check(client, review, ds)).status_code == 404


async def test_review_input_limits(client, sign_in, fake_llm_critic, fake_llm):
    await sign_in("alice")
    prompt = await make_prompt(client)
    version_id = prompt["versions"][0]["id"]
    bad = [
        {"system": "a" * 10_000, "user_template": "b" * 10_001},  # 20001 characters
        {"system": "a" * 20_001},
        {"prompt_version_id": version_id, "system": "x"},  # two sources
        {"prompt_version_id": version_id, "user_template": "x"},
        {},  # none
        {"system": "  ", "user_template": ""},  # nothing but blanks
        {"prompt_version_id": "nope"},
        {"system": "a\x00"},  # Postgres text cannot hold NUL
    ]
    for body in bad:
        r = await client.post("/api/review", json=body)
        assert r.status_code == 422, body
    assert fake_llm.calls == []

    # exactly 20000 characters pass, and either field may be the only one
    fake_llm_critic("a" * 20_000, "")
    assert (await client.post("/api/review", json={"system": "a" * 20_000})).status_code == 201
    fake_llm_critic("", "b {{x}}")
    assert (await client.post("/api/review", json={"user_template": "b {{x}}"})).status_code == 201


async def test_review_of_long_version_is_rejected(client, sign_in, fake_llm):
    await sign_in("alice")
    prompt = await make_prompt(client, version={**VERSION, "system": "a" * 20_001})
    r = await client.post("/api/review", json={"prompt_version_id": prompt["versions"][0]["id"]})
    assert r.status_code == 422
    assert fake_llm.calls == []


@pytest.mark.parametrize("failure", ["schema", "refusal", "api"])
async def test_critic_failure_is_502_and_leaves_no_prompt(
    client, sign_in, fake_llm_critic, fake_llm, failure
):
    await sign_in("alice")
    if failure == "schema":
        fake_llm_critic(SYSTEM, TEMPLATE, sections=[])
    else:
        original = fake_llm.complete

        async def complete(req):
            if failure == "api":
                raise anthropic.APIConnectionError(
                    request=httpx.Request("POST", "http://anthropic")
                )
            fake_llm_critic(SYSTEM, TEMPLATE)
            return dataclasses.replace(await original(req), stop_reason="refusal", json=None)

        fake_llm.complete = complete
    r = await client.post("/api/review", json={"system": SYSTEM, "user_template": TEMPLATE})
    assert r.status_code == 502, r.text
    assert isinstance(r.json()["detail"], str)
    assert (await client.get("/api/evals/prompts")).json() == []
