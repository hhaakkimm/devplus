import pytest

from app.core.errors import NotFound
from app.modules.evals.schemas import VersionIn
from app.modules.evals.service import PromptService

V = {"system": "s", "user_template": "Say {{word}}", "model": "claude-haiku-5-5"}
NOT_AUTHOR = {"detail": "Только автор может изменять"}


async def make_prompt(client, name="P", version=V):
    r = await client.post("/api/evals/prompts", json={"name": name, "version": version})
    assert r.status_code == 201, r.text
    return r.json()


async def test_requires_session(client):
    assert (await client.get("/api/evals/prompts")).status_code == 401


async def test_create_returns_detail_with_defaults(client, sign_in):
    await sign_in("alice")
    p = await make_prompt(client)
    assert (p["name"], p["shared"], p["owner_login"], p["latest_version"]) == (
        "P",
        False,
        "alice",
        1,
    )
    [v] = p["versions"]
    assert (v["number"], v["effort"], v["max_tokens"], v["output_schema"]) == (
        1,
        "medium",
        1024,
        None,
    )


async def test_versions_are_numbered_and_immutable(client, sign_in):
    await sign_in("alice")
    p = await make_prompt(client)
    r = await client.post(f"/api/evals/prompts/{p['id']}/versions", json=V | {"system": "new"})
    assert r.status_code == 201
    v2 = r.json()
    detail = (await client.get(f"/api/evals/prompts/{p['id']}")).json()
    assert [v["number"] for v in detail["versions"]] == [1, 2]
    assert v2["number"] == 2
    assert [v["system"] for v in detail["versions"]] == ["s", "new"]  # v1 untouched
    assert detail["latest_version"] == 2


async def test_private_prompt_is_404_for_others(client, sign_in):
    await sign_in("alice")
    p = await make_prompt(client)
    await sign_in("bob")
    url = f"/api/evals/prompts/{p['id']}"
    assert (await client.get(url)).status_code == 404
    assert (await client.patch(url, json={"shared": True})).status_code == 404
    assert (await client.post(f"{url}/versions", json=V)).status_code == 404
    assert (await client.post(f"{url}/copy")).status_code == 404
    assert (await client.get("/api/evals/prompts")).json() == []


async def test_unknown_prompt_is_404(client, sign_in):
    await sign_in("alice")
    r = await client.get("/api/evals/prompts/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert "detail" in r.json()


async def test_shared_prompt_visible_but_not_editable(client, sign_in):
    await sign_in("alice")
    p = await make_prompt(client)
    url = f"/api/evals/prompts/{p['id']}"
    assert (await client.patch(url, json={"shared": True})).status_code == 200
    await sign_in("bob")
    assert (await client.get(url)).status_code == 200
    r = await client.post(f"{url}/versions", json=V)
    assert (r.status_code, r.json()) == (403, NOT_AUTHOR)
    r = await client.patch(url, json={"name": "mine"})
    assert (r.status_code, r.json()) == (403, NOT_AUTHOR)
    listed = (await client.get("/api/evals/prompts")).json()
    assert [(x["name"], x["owner_login"]) for x in listed] == [("P", "alice")]


async def test_patch_name_and_shared(client, sign_in):
    await sign_in("alice")
    p = await make_prompt(client)
    url = f"/api/evals/prompts/{p['id']}"
    r = await client.patch(url, json={"name": "  Renamed "})
    assert (r.json()["name"], r.json()["shared"]) == ("Renamed", False)
    r = await client.patch(url, json={"shared": True})
    assert (r.json()["name"], r.json()["shared"]) == ("Renamed", True)
    assert (await client.patch(url, json={"name": " "})).status_code == 422
    assert (await client.patch(url, json={"name": "x" * 201})).status_code == 422


async def test_copy_creates_own_prompt_with_v1(client, sign_in):
    await sign_in("alice")
    p = await make_prompt(client)
    url = f"/api/evals/prompts/{p['id']}"
    await client.patch(url, json={"shared": True})
    await client.post(f"{url}/versions", json=V | {"system": "latest", "max_tokens": 77})
    await sign_in("bob")
    r = await client.post(f"{url}/copy")
    assert r.status_code == 201
    c = r.json()
    assert c["id"] != p["id"]
    assert (c["owner_login"], c["name"], c["shared"]) == ("bob", "P (копия)", False)
    assert [(v["number"], v["system"], v["max_tokens"]) for v in c["versions"]] == [
        (1, "latest", 77)
    ]
    names = [x["name"] for x in (await client.get("/api/evals/prompts")).json()]
    assert sorted(names) == ["P", "P (копия)"]  # own copy plus alice's shared original


async def test_copy_keeps_name_within_limit(client, sign_in):
    await sign_in("alice")
    p = await make_prompt(client, name="n" * 200)
    r = await client.post(f"/api/evals/prompts/{p['id']}/copy")
    assert len(r.json()["name"]) == 200
    assert r.json()["name"].endswith(" (копия)")


async def test_trainer_prompts_hidden_from_lab_list(client, sign_in, db_session):
    alice = await sign_in("alice")
    t = await PromptService(db_session).create(
        alice, "Task", VersionIn.model_validate(V), trainer_task="intro/task-1"
    )
    assert (await client.get("/api/evals/prompts")).json() == []
    assert (
        await client.get(f"/api/evals/prompts/{t.id}")
    ).status_code == 200  # owner still sees it
    # sharing a trainer prompt must not expose it
    await client.patch(f"/api/evals/prompts/{t.id}", json={"shared": True})
    await sign_in("bob")
    assert (await client.get("/api/evals/prompts")).json() == []
    assert (await client.get(f"/api/evals/prompts/{t.id}")).status_code == 404


async def test_get_version_follows_prompt_access(client, sign_in, db_session):
    alice = await sign_in("alice")
    p = await make_prompt(client)
    version_id = p["versions"][0]["id"]
    bob = await sign_in("bob")
    service = PromptService(db_session)
    assert (await service.get_version(alice, version_id)).number == 1
    with pytest.raises(NotFound):
        await service.get_version(bob, version_id)
    await sign_in("alice")
    await client.patch(f"/api/evals/prompts/{p['id']}", json={"shared": True})
    assert str((await service.get_version(bob, version_id)).id) == version_id


@pytest.mark.parametrize(
    "patch",
    [
        {"max_tokens": 16001},
        {"max_tokens": 0},
        {"model": "gpt-4"},
        {"effort": "extreme"},
        {"system": "a" * 50_000, "user_template": "b"},
        {"output_schema": {"type": 5}},
        {"output_schema": {"$schema": []}},  # would crash validator_for
        {"output_schema": {"$schema": 5}},
        {"output_schema": {"type": "object", "description": "x" * 65_536}},
    ],
)
async def test_version_validation(client, sign_in, patch):
    await sign_in("alice")
    r = await client.post("/api/evals/prompts", json={"name": "P", "version": V | patch})
    assert r.status_code == 422
    p = await make_prompt(client)
    r = await client.post(f"/api/evals/prompts/{p['id']}/versions", json=V | patch)
    assert r.status_code == 422


async def test_version_limits_are_inclusive(client, sign_in):
    await sign_in("alice")
    schema = {"type": "object", "properties": {"a": {"type": "string"}}}
    version = V | {
        "system": "a" * 49_999,
        "user_template": "b",
        "max_tokens": 16000,
        "effort": "max",
        "model": "claude-opus-5-5",
        "output_schema": schema,
    }
    p = await make_prompt(client, version=version)
    assert p["versions"][0]["output_schema"] == schema


@pytest.mark.parametrize("name", ["", "   ", "x" * 201])
async def test_prompt_name_validation(client, sign_in, name):
    await sign_in("alice")
    r = await client.post("/api/evals/prompts", json={"name": name, "version": V})
    assert r.status_code == 422
