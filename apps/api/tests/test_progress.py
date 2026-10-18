import pytest


async def test_progress_requires_session(client):
    assert (await client.get("/api/progress")).status_code == 401
    assert (await client.put("/api/progress/internet/dns")).status_code == 401


async def test_mark_and_unmark_are_idempotent(client, sign_in):
    await sign_in()
    for _ in range(2):
        assert (await client.put("/api/progress/internet/dns")).status_code == 204
    completed = (await client.get("/api/progress")).json()["completed"]
    assert [c["lesson_slug"] for c in completed] == ["internet/dns"]
    for _ in range(2):
        assert (await client.delete("/api/progress/internet/dns")).status_code == 204
    assert (await client.get("/api/progress")).json() == {"completed": []}


@pytest.mark.parametrize("path", ["Internet/dns", "internet/dn_s", "internet/d%20ns"])
async def test_bad_slug_is_422(client, sign_in, path):
    await sign_in()
    assert (await client.put(f"/api/progress/{path}")).status_code == 422


async def test_slug_longer_than_200_is_400(client, sign_in):
    await sign_in()
    r = await client.put(f"/api/progress/{'a' * 100}/{'b' * 100}")  # 201 chars with the slash
    assert r.status_code == 400
    assert r.json() == {"detail": "Lesson slug too long"}


async def test_progress_is_per_user(client, sign_in):
    await sign_in("alice")
    await client.put("/api/progress/internet/dns")
    await sign_in("bob")
    assert (await client.get("/api/progress")).json() == {"completed": []}
