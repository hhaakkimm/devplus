import pytest

PUT = "/api/quizzes/core-concepts/caching/result"


async def test_quiz_requires_session(client):
    assert (await client.get("/api/quizzes/results")).status_code == 401
    assert (await client.put(PUT, json={"score": 1, "total": 2})).status_code == 401


async def test_empty_results(client, sign_in):
    await sign_in()
    assert (await client.get("/api/quizzes/results")).json() == {"results": []}


async def test_first_attempt_creates_result(client, sign_in):
    await sign_in()
    assert (await client.put(PUT, json={"score": 7, "total": 10})).status_code == 204
    [r] = (await client.get("/api/quizzes/results")).json()["results"]
    assert (r["quiz_slug"], r["best_score"], r["total"], r["attempts"]) == (
        "core-concepts/caching",
        7,
        10,
        1,
    )


async def test_worse_attempt_keeps_best_but_counts(client, sign_in):
    await sign_in()
    await client.put(PUT, json={"score": 8, "total": 10})
    await client.put(PUT, json={"score": 3, "total": 10})
    [r] = (await client.get("/api/quizzes/results")).json()["results"]
    assert (r["best_score"], r["attempts"]) == (8, 2)


async def test_better_attempt_replaces_best(client, sign_in):
    await sign_in()
    await client.put(PUT, json={"score": 3, "total": 10})
    await client.put(PUT, json={"score": 9, "total": 10})
    [r] = (await client.get("/api/quizzes/results")).json()["results"]
    assert (r["best_score"], r["attempts"]) == (9, 2)


async def test_best_is_compared_by_share_when_quiz_grew(client, sign_in):
    await sign_in()
    await client.put(PUT, json={"score": 5, "total": 10})  # 50%
    await client.put(PUT, json={"score": 6, "total": 15})  # 40%: worse, best stays 5 of 10
    [r] = (await client.get("/api/quizzes/results")).json()["results"]
    assert (r["best_score"], r["total"], r["attempts"]) == (5, 10, 2)
    await client.put(PUT, json={"score": 12, "total": 15})  # 80%: new best with its own total
    [r] = (await client.get("/api/quizzes/results")).json()["results"]
    assert (r["best_score"], r["total"], r["attempts"]) == (12, 15, 3)


@pytest.mark.parametrize(
    "body",
    [
        {"score": 11, "total": 10},
        {"score": -1, "total": 10},
        {"score": 0, "total": 0},
        {"score": 1, "total": 201},
        {"score": "a", "total": 10},
        {"total": 10},
    ],
)
async def test_bad_result_is_422(client, sign_in, body):
    await sign_in()
    assert (await client.put(PUT, json=body)).status_code == 422


@pytest.mark.parametrize("path", ["Core/caching", "core/ca_ching", "core/ca%20ching"])
async def test_bad_slug_is_422(client, sign_in, path):
    await sign_in()
    r = await client.put(f"/api/quizzes/{path}/result", json={"score": 1, "total": 2})
    assert r.status_code == 422


async def test_slug_longer_than_200_is_400(client, sign_in):
    await sign_in()
    r = await client.put(
        f"/api/quizzes/{'a' * 100}/{'b' * 100}/result", json={"score": 1, "total": 2}
    )
    assert r.status_code == 400
    assert r.json() == {"detail": "Quiz slug too long"}


async def test_results_are_per_user(client, sign_in):
    await sign_in("alice")
    await client.put(PUT, json={"score": 1, "total": 2})
    await sign_in("bob")
    assert (await client.get("/api/quizzes/results")).json() == {"results": []}
