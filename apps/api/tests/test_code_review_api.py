from pathlib import Path

import pytest
from sqlalchemy import select

from app.modules.code_review.judge import IssueResult, ReviewResult, SectionResult
from app.modules.code_review.models import ReviewAttempt
from app.modules.code_review.service import CodeReviewService

FIXTURES = Path(__file__).parent / "fixtures" / "code_review"
TASK = "/api/code-review/tasks/start/demo"
ATTEMPTS = f"{TASK}/attempts"
KEY = "start/demo"
COMMENT = {"file": "worker.py", "line_start": 18, "line_end": 22, "text": "Гонка при выборе"}
DRAFT = {"comments": [COMMENT], "verdict": "request_changes", "summary": "Не мёрджить"}
HIDDEN = (
    "СЕКРЕТ-NOTES",
    "СЕКРЕТ-WHY",
    "Задание выбирается вне блокировки",  # an issue description
    "SQL собирается f-строкой",
    '"issues"',
    '"traps"',
    '"notes"',
    '"expected_verdict"',
    '"why_fine"',
    '"reference"',
)


@pytest.fixture
def settings(settings):
    return settings.model_copy(update={"content_dir": str(FIXTURES)})


async def new_attempt(client) -> dict:
    return (await client.post(ATTEMPTS)).json()


def result(passed: bool) -> dict:
    return ReviewResult(
        score=0.9 if passed else 0.2,
        passed=passed,
        verdict="request_changes",
        verdict_matches=True,
        issues=[
            IssueResult(id="race-on-claim", found=True, score=5, reason="Нашёл гонку"),
            IssueResult(id="sql-format", found=False, score=1, reason="Не заметил SQL"),
        ],
        general=[SectionResult(name="Ложные замечания", score=5, reason="Чисто")],
        comment="Хорошо",
    ).model_dump()


async def add_attempt(db_session, user, status: str, passed: bool | None = None) -> ReviewAttempt:
    row = ReviewAttempt(
        user_id=user.id,
        task_key=KEY,
        status=status,
        comments=[COMMENT],
        verdict="request_changes",
        result=None if passed is None else result(passed),
    )
    db_session.add(row)
    await db_session.commit()
    return row


async def test_requires_login(client):
    some_id = "00000000-0000-0000-0000-000000000000"
    for method, url in [
        ("GET", "/api/code-review/tasks"),
        ("GET", TASK),
        ("POST", ATTEMPTS),
        ("PUT", f"/api/code-review/attempts/{some_id}"),
        ("GET", f"/api/code-review/attempts/{some_id}"),
        ("GET", "/api/code-review/attempts"),
    ]:
        resp = await client.request(method, url, json={"comments": []} if method == "PUT" else None)
        assert resp.status_code == 401, (method, url)


async def test_task_list_and_get(client, sign_in):
    await sign_in("alice")
    [task] = (await client.get("/api/code-review/tasks")).json()
    assert task == {
        "module": "start",
        "slug": "demo",
        "title": "Воркер очереди заданий",
        "difficulty": "medium",
        "estimate_min": 15,
        "status": "not_started",
    }
    got = (await client.get(TASK)).json()
    assert set(got["files"]) == {"worker.py", "store.py"}
    assert "import threading" in got["files"]["worker.py"]
    assert "Корректность при нескольких воркерах" in got["statement"]
    assert set(got) == {
        "module",
        "slug",
        "title",
        "difficulty",
        "estimate_min",
        "statement",
        "files",
    }


async def test_list_status(client, sign_in, db_session):
    user = await sign_in("alice")

    async def status() -> str:
        return (await client.get("/api/code-review/tasks")).json()[0]["status"]

    await add_attempt(db_session, user, "draft")
    assert await status() == "attempted"
    await add_attempt(db_session, user, "graded", passed=False)
    assert await status() == "attempted"
    await add_attempt(db_session, user, "graded", passed=True)
    assert await status() == "passed"
    await sign_in("bob")  # another user's passes do not count
    assert await status() == "not_started"


async def test_no_hidden_data_before_graded(client, sign_in):
    await sign_in("alice")
    responses = [await client.get(TASK), await client.post(ATTEMPTS)]
    attempt_id = responses[1].json()["id"]
    responses += [
        await client.put(f"/api/code-review/attempts/{attempt_id}", json=DRAFT),
        await client.get(f"/api/code-review/attempts/{attempt_id}"),
        await client.get("/api/code-review/attempts"),
    ]
    for resp in responses:
        assert resp.status_code in (200, 201), resp.text
        for secret in HIDDEN:
            assert secret not in resp.text, (resp.request.url, secret)
    assert responses[3].json()["revealed"] is None


@pytest.mark.parametrize("module", ["../x", "nope", "start%2F..%2Fx"])
async def test_unknown_task_404(client, sign_in, module):
    await sign_in("alice")
    assert (await client.get(f"/api/code-review/tasks/{module}/demo")).status_code == 404
    assert (await client.post(f"/api/code-review/tasks/{module}/demo/attempts")).status_code == 404
    assert (await client.get("/api/code-review/tasks/start/nope")).status_code == 404
    assert (await client.post("/api/code-review/tasks/start/nope/attempts")).status_code == 404


async def test_create_attempt_is_idempotent_for_draft(client, sign_in, db_session):
    user = await sign_in("alice")
    resp = await client.post(ATTEMPTS)
    assert resp.status_code == 201
    first = resp.json()
    assert (first["status"], first["task_key"], first["comments"]) == ("draft", KEY, [])
    assert (await client.post(ATTEMPTS)).json()["id"] == first["id"]
    assert len((await client.get("/api/code-review/attempts")).json()) == 1
    # once the draft is no longer a draft, a new one is created
    row = await db_session.get(ReviewAttempt, first["id"])
    row.status = "graded"
    await db_session.commit()
    assert (await client.post(ATTEMPTS)).json()["id"] != first["id"]
    assert row.user_id == user.id


async def test_create_attempt_returns_the_draft_of_a_simultaneous_request(
    client, sign_in, db_session, monkeypatch
):
    user = await sign_in("alice")
    existing = await add_attempt(db_session, user, "draft")
    original = CodeReviewService._draft
    misses = []

    async def miss_once(self, user, key):
        if not misses:  # the first lookup runs before the other request has committed
            misses.append(1)
            return None
        return await original(self, user, key)

    monkeypatch.setattr(CodeReviewService, "_draft", miss_once)
    resp = await client.post(ATTEMPTS)
    assert resp.status_code == 201
    assert resp.json()["id"] == str(existing.id)
    assert misses == [1]
    drafts = await db_session.scalars(
        select(ReviewAttempt).where(
            ReviewAttempt.user_id == user.id, ReviewAttempt.status == "draft"
        )
    )
    assert [d.id for d in drafts] == [existing.id]


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"comments": [{**COMMENT, "line_start": 5, "line_end": 4}]}, id="start>end"),
        pytest.param({"comments": [{**COMMENT, "line_start": 0}]}, id="start 0"),
        pytest.param({"comments": [{**COMMENT, "line_end": 32}]}, id="past the last line"),
        pytest.param(
            {"comments": [{**COMMENT, "file": "store.py", "line_end": 18}]}, id="past other file"
        ),
        pytest.param({"comments": [{**COMMENT, "file": "../x"}]}, id="file ../x"),
        pytest.param({"comments": [{**COMMENT, "file": "nope.py"}]}, id="unknown file"),
        pytest.param({"comments": [COMMENT] * 51}, id="51 comments"),
        pytest.param({"comments": [{**COMMENT, "text": "я" * 2001}]}, id="text 2001"),
        pytest.param({"comments": [], "summary": "я" * 4001}, id="summary 4001"),
        pytest.param({"comments": [], "verdict": "maybe"}, id="unknown verdict"),
    ],
)
async def test_draft_validation_422(client, sign_in, body):
    await sign_in("alice")
    attempt = await new_attempt(client)
    resp = await client.put(f"/api/code-review/attempts/{attempt['id']}", json=body)
    assert resp.status_code == 422
    assert (await client.get(f"/api/code-review/attempts/{attempt['id']}")).json()["comments"] == []


async def test_draft_accepts_the_last_line_and_the_limits(client, sign_in):
    await sign_in("alice")
    attempt = await new_attempt(client)
    body = {
        "comments": [{**COMMENT, "line_end": 31, "text": "я" * 2000}] * 50,
        "summary": "я" * 4000,
    }
    resp = await client.put(f"/api/code-review/attempts/{attempt['id']}", json=body)
    assert resp.status_code == 200, resp.text


async def test_save_draft_roundtrip(client, sign_in):
    await sign_in("alice")
    attempt = await new_attempt(client)
    url = f"/api/code-review/attempts/{attempt['id']}"
    saved = (await client.put(url, json=DRAFT)).json()
    got = (await client.get(url)).json()
    assert got == saved
    assert got["comments"] == [COMMENT]
    assert (got["verdict"], got["summary"], got["status"]) == (
        "request_changes",
        "Не мёрджить",
        "draft",
    )
    # a second save replaces the first
    await client.put(url, json={"comments": []})
    got = (await client.get(url)).json()
    assert (got["comments"], got["verdict"], got["summary"]) == ([], None, None)


async def test_other_users_attempt_404(client, sign_in):
    await sign_in("alice")
    attempt = await new_attempt(client)
    url = f"/api/code-review/attempts/{attempt['id']}"
    await sign_in("bob")
    assert (await client.get(url)).status_code == 404
    assert (await client.put(url, json=DRAFT)).status_code == 404
    assert (await client.get("/api/code-review/attempts")).json() == []


async def test_cannot_edit_after_submit(client, sign_in, db_session):
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, "graded", passed=True)
    resp = await client.put(f"/api/code-review/attempts/{row.id}", json=DRAFT)
    assert resp.status_code == 409


async def test_graded_attempt_reveals_without_notes(client, sign_in, db_session):
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, "graded", passed=True)
    resp = await client.get(f"/api/code-review/attempts/{row.id}")
    body = resp.json()
    assert "СЕКРЕТ-NOTES" not in resp.text
    assert body["result"]["passed"] is True
    revealed = body["revealed"]
    assert revealed["expected_verdict"] == "request_changes"
    assert revealed["issues"][0] == {
        "id": "race-on-claim",
        "file": "worker.py",
        "lines": [18, 22],
        "critical": True,
        "description": (
            "Задание выбирается вне блокировки, а помечается внутри неё, "
            "два воркера забирают одно задание."
        ),
        "found": True,
        "score": 5,
        "reason": "Нашёл гонку",
    }
    assert [i["found"] for i in revealed["issues"]] == [True, False]
    [trap] = revealed["traps"]
    assert (trap["file"], trap["lines"]) == ("worker.py", [28, 30])
    assert "СЕКРЕТ-WHY" in trap["why_fine"]
    assert "notes" not in resp.text
