import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from app.modules.code_review.judge import (
    IssueResult,
    ReviewResult,
    SectionResult,
    build_grader,
    judge_expected,
    judge_inputs,
    judge_output,
)
from app.modules.code_review.models import ReviewAttempt, ReviewFeedbackReport
from app.modules.code_review.service import GRADING_TIMEOUT, CodeReviewService
from app.modules.code_review.tasks import FALSE_FINDINGS, PRIORITIES, ReviewComment, load_tasks
from app.modules.evals.judge import judge_user

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
        ("POST", f"/api/code-review/attempts/{some_id}/submit"),
        ("POST", f"/api/code-review/attempts/{some_id}/report"),
    ]:
        body = {"comments": []} if method == "PUT" else {"text": "x"}
        resp = await client.request(method, url, json=body if method != "GET" else None)
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


# --- submit, grading, report ---

[SPEC] = load_tasks(FIXTURES)
RACE, SQL = "race-on-claim", "sql-format"
ALL_5 = dict.fromkeys([RACE, SQL, FALSE_FINDINGS, PRIORITIES], 5)
CRITICAL_MISSED = {**ALL_5, RACE: 2}


def script(llm, scores, body=DRAFT) -> None:
    """The judge's answer to exactly this review of the demo task."""
    answer = {
        "sections": [{"name": n, "score": v, "reason": f"r-{n}"} for n, v in scores.items()],
        "comment": "итог",
    }
    key = judge_user(
        build_grader(SPEC),
        judge_inputs(SPEC),
        judge_expected(SPEC),
        judge_output(
            [ReviewComment(**c) for c in body["comments"]], body["verdict"], body.get("summary")
        ),
    )
    llm.responses = {**(llm.responses or {}), key: json.dumps(answer)}


async def draft_attempt(client, body=DRAFT) -> str:
    attempt = await new_attempt(client)
    resp = await client.put(f"/api/code-review/attempts/{attempt['id']}", json=body)
    assert resp.status_code == 200, resp.text
    return attempt["id"]


def submit_url(attempt_id) -> str:
    return f"/api/code-review/attempts/{attempt_id}/submit"


@pytest.fixture
def limit_2(settings):
    settings.code_review_daily_limit = 2


@pytest.fixture
def lenient(settings, tmp_path):
    """The demo task with a threshold below what a missed critical issue can score."""
    dst = tmp_path / "content"
    shutil.copytree(FIXTURES, dst)
    task_yaml = next(dst.rglob("task.yaml"))
    task_yaml.write_text(task_yaml.read_text().replace("threshold: 0.7", "threshold: 0.5"))
    settings.content_dir = str(dst)


async def test_submit_happy_path(client, sign_in, fake_llm, db_session):
    await sign_in("alice")
    attempt_id = await draft_attempt(client)
    script(fake_llm, ALL_5)
    resp = await client.post(submit_url(attempt_id))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "graded"
    assert body["result"]["passed"] is True
    assert body["result"]["verdict_matches"] is True
    assert body["submitted_at"] is not None
    [issue, _] = body["revealed"]["issues"]
    assert "Задание выбирается вне блокировки" in issue["description"]
    assert issue["found"] is True
    assert "СЕКРЕТ-WHY" in body["revealed"]["traps"][0]["why_fine"]  # the trap is shown
    assert "СЕКРЕТ-NOTES" not in resp.text
    assert len(fake_llm.calls) == 1
    assert (await client.get(f"/api/code-review/attempts/{attempt_id}")).json() == body
    row = await db_session.get(ReviewAttempt, attempt_id)
    await db_session.refresh(row)
    assert row.status == "graded" and row.cost_usd is not None and row.cost_usd > 0


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"comments": [COMMENT]}, id="no verdict"),
        pytest.param({"comments": [], "verdict": "approve"}, id="nothing written"),
        pytest.param({"comments": [], "verdict": "approve", "summary": "  \n"}, id="blank summary"),
    ],
)
async def test_submit_requires_verdict_and_content(client, sign_in, fake_llm, body):
    await sign_in("alice")
    attempt_id = await draft_attempt(client, body)
    resp = await client.post(submit_url(attempt_id))
    assert resp.status_code == 422
    assert fake_llm.calls == []
    got = (await client.get(f"/api/code-review/attempts/{attempt_id}")).json()
    assert got["status"] == "draft"  # still editable


async def test_submit_with_only_a_summary(client, sign_in, fake_llm):
    await sign_in("alice")
    body = {"comments": [], "verdict": "approve", "summary": "Выглядит нормально"}
    attempt_id = await draft_attempt(client, body)
    script(fake_llm, CRITICAL_MISSED, body)
    assert (await client.post(submit_url(attempt_id))).status_code == 200


async def test_submit_revalidates_stored_comments(client, sign_in, fake_llm, db_session):
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, "draft")
    row.comments = [{**COMMENT, "line_end": 99}]  # the task file has changed since the draft
    await db_session.commit()
    resp = await client.post(submit_url(row.id))
    assert resp.status_code == 422
    assert fake_llm.calls == []
    await db_session.refresh(row)
    assert row.status == "draft"


async def test_submit_unknown_or_foreign_attempt_404(client, sign_in, fake_llm):
    await sign_in("alice")
    attempt_id = await draft_attempt(client)
    assert (
        await client.post(submit_url("00000000-0000-0000-0000-000000000000"))
    ).status_code == 404
    await sign_in("bob")
    assert (await client.post(submit_url(attempt_id))).status_code == 404
    assert fake_llm.calls == []


async def test_critical_miss_fails_even_with_high_score(client, sign_in, fake_llm, lenient):
    await sign_in("alice")
    attempt_id = await draft_attempt(client)
    script(fake_llm, CRITICAL_MISSED)
    body = (await client.post(submit_url(attempt_id))).json()
    assert body["status"] == "graded"
    assert body["result"]["score"] >= 0.5
    assert body["result"]["passed"] is False
    assert body["revealed"]["issues"][0]["found"] is False


async def test_judge_failure_marks_failed_and_can_be_resent(client, sign_in, fake_llm, db_session):
    await sign_in("alice")
    attempt_id = await draft_attempt(client)
    script(fake_llm, {RACE: 5})  # sections that do not match the rubric
    resp = await client.post(submit_url(attempt_id))
    assert resp.status_code == 200
    body = resp.json()
    assert (body["status"], body["result"], body["revealed"]) == ("failed", None, None)
    row = await db_session.get(ReviewAttempt, attempt_id)
    await db_session.refresh(row)
    assert row.result == {"error": "Разделы судьи не совпадают с рубрикой"}
    assert row.cost_usd is not None and row.cost_usd > 0  # paid for even so
    script(fake_llm, ALL_5)
    resp = await client.post(submit_url(attempt_id))
    assert resp.json()["status"] == "graded"
    await db_session.refresh(row)
    assert row.status == "graded" and row.cost_usd > 0
    assert len(fake_llm.calls) == 2


async def test_llm_exception_leaves_attempt_failed_and_retryable(
    client, sign_in, fake_llm, db_session
):
    await sign_in("alice")
    attempt_id = await draft_attempt(client)
    original = fake_llm.complete

    async def boom(req):
        raise ConnectionError("network down")

    fake_llm.complete = boom
    resp = await client.post(submit_url(attempt_id))
    assert resp.status_code == 502
    assert "detail" in resp.json()
    row = await db_session.get(ReviewAttempt, attempt_id)
    await db_session.refresh(row)
    assert row.status == "failed" and row.result == {"error": "Судья недоступен"}
    fake_llm.complete = original
    script(fake_llm, ALL_5)
    assert (await client.post(submit_url(attempt_id))).json()["status"] == "graded"


async def test_daily_limit(client, sign_in, fake_llm, db_session, limit_2):
    user = await sign_in("alice")
    script(fake_llm, ALL_5)
    await add_attempt(db_session, user, "failed")  # does not count
    for _ in range(2):
        attempt_id = await draft_attempt(client)
        assert (await client.post(submit_url(attempt_id))).status_code == 200
    attempt_id = await draft_attempt(client)
    resp = await client.post(submit_url(attempt_id))
    assert resp.status_code == 409
    assert "лимит" in resp.json()["detail"].lower()
    assert len(fake_llm.calls) == 2
    got = (await client.get(f"/api/code-review/attempts/{attempt_id}")).json()
    assert got["status"] == "draft"
    # another user is not affected, and an attempt sent more than a day ago does not count
    await sign_in("bob")
    other = await draft_attempt(client)
    assert (await client.post(submit_url(other))).status_code == 200
    await sign_in("alice")
    old = await db_session.scalars(
        select(ReviewAttempt).where(
            ReviewAttempt.status == "graded", ReviewAttempt.user_id == user.id
        )
    )
    first = old.first()
    first.submitted_at = datetime.now(UTC) - timedelta(hours=25)
    await db_session.commit()
    assert (await client.post(submit_url(attempt_id))).status_code == 200


async def test_fresh_grading_counts_for_the_limit(client, sign_in, fake_llm, db_session, limit_2):
    user = await sign_in("alice")
    for _ in range(2):
        row = await add_attempt(db_session, user, "grading")
        row.submitted_at = datetime.now(UTC)
    await db_session.commit()
    attempt_id = await draft_attempt(client)
    assert (await client.post(submit_url(attempt_id))).status_code == 409
    assert fake_llm.calls == []


async def test_double_submit_one_judge_call(client, sign_in, fake_llm):
    await sign_in("alice")
    attempt_id = await draft_attempt(client)
    script(fake_llm, ALL_5)
    assert (await client.post(submit_url(attempt_id))).status_code == 200
    assert (await client.post(submit_url(attempt_id))).status_code == 409  # graded
    assert len(fake_llm.calls) == 1


async def test_submit_of_a_row_that_left_draft_in_between_is_409(
    client, sign_in, fake_llm, db_session, monkeypatch
):
    """The submit that lost the race read a draft, but another one has moved it on already."""
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, "grading")
    row.submitted_at = datetime.now(UTC)
    await db_session.commit()
    original = CodeReviewService._own

    async def stale_read(self, *args, **kwargs):
        seen = await original(self, *args, **kwargs)
        return ReviewAttempt(  # a copy that still says draft
            id=seen.id,
            user_id=seen.user_id,
            task_key=seen.task_key,
            status="draft",
            comments=seen.comments,
            verdict=seen.verdict,
        )

    monkeypatch.setattr(CodeReviewService, "_own", stale_read)
    assert (await client.post(submit_url(row.id))).status_code == 409
    assert fake_llm.calls == []
    await db_session.refresh(row)
    assert row.status == "grading"


async def test_draft_save_cannot_overwrite_an_attempt_in_grading(
    client, sign_in, db_session, monkeypatch
):
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, "grading")
    original = CodeReviewService._own

    async def stale_read(self, *args, **kwargs):
        seen = await original(self, *args, **kwargs)
        return ReviewAttempt(
            id=seen.id, user_id=seen.user_id, task_key=seen.task_key, status="draft"
        )

    monkeypatch.setattr(CodeReviewService, "_own", stale_read)
    resp = await client.put(f"/api/code-review/attempts/{row.id}", json={"comments": []})
    assert resp.status_code == 409
    await db_session.refresh(row)
    assert row.comments == [COMMENT] and row.verdict == "request_changes"


async def test_stale_grading_is_failed(client, sign_in, fake_llm, db_session):
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, "grading", passed=True)
    row.submitted_at = datetime.now(UTC) - GRADING_TIMEOUT - timedelta(seconds=5)
    await db_session.commit()
    url = f"/api/code-review/attempts/{row.id}"
    got = (await client.get(url)).json()
    assert (got["status"], got["result"], got["revealed"]) == ("failed", None, None)
    assert [a["status"] for a in (await client.get("/api/code-review/attempts")).json()] == [
        "failed"
    ]
    script(fake_llm, ALL_5, {"comments": [COMMENT], "verdict": "request_changes"})
    resp = await client.post(submit_url(row.id))
    assert resp.status_code == 200
    assert resp.json()["status"] == "graded"
    assert resp.json()["result"]["comment"] == "итог"  # a fresh result, not the stored one


async def test_fresh_grading_cannot_be_submitted_again(client, sign_in, fake_llm, db_session):
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, "grading")
    row.submitted_at = datetime.now(UTC) - GRADING_TIMEOUT + timedelta(minutes=1)
    await db_session.commit()
    assert (await client.get(f"/api/code-review/attempts/{row.id}")).json()["status"] == "grading"
    assert (await client.post(submit_url(row.id))).status_code == 409
    assert fake_llm.calls == []


@pytest.mark.parametrize("status", ["grading", "failed"])
async def test_stored_result_of_a_non_graded_attempt_stays_hidden(
    client, sign_in, db_session, status
):
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, status, passed=True)
    row.submitted_at = datetime.now(UTC)
    await db_session.commit()
    for url in (f"/api/code-review/attempts/{row.id}", "/api/code-review/attempts"):
        resp = await client.get(url)
        assert resp.status_code == 200
        assert "race-on-claim" not in resp.text
        assert "Нашёл гонку" not in resp.text
    got = (await client.get(f"/api/code-review/attempts/{row.id}")).json()
    assert (got["status"], got["result"], got["revealed"]) == (status, None, None)


async def test_failed_attempt_with_error_result_is_listed(client, sign_in, db_session):
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, "failed")
    row.result = {"error": "Судья отказался отвечать"}
    await db_session.commit()
    resp = await client.get("/api/code-review/attempts")
    assert resp.status_code == 200 and resp.json()[0]["result"] is None


async def test_graded_attempt_of_a_changed_task_does_not_break_the_list(
    client, sign_in, db_session
):
    user = await sign_in("alice")
    good = await add_attempt(db_session, user, "graded", passed=True)
    gone = await add_attempt(db_session, user, "graded", passed=True)
    gone.task_key = "start/removed"
    renamed = await add_attempt(db_session, user, "graded", passed=True)
    changed = result(True)
    changed["issues"][0]["id"] = "old-issue-id"
    renamed.result = changed
    await db_session.commit()
    resp = await client.get("/api/code-review/attempts")
    assert resp.status_code == 200, resp.text
    by_id = {a["id"]: a for a in resp.json()}
    assert by_id[str(good.id)]["revealed"] is not None
    for stale in (gone, renamed):
        got = by_id[str(stale.id)]
        assert (got["status"], got["revealed"]) == ("graded", None)
        assert got["result"]["passed"] is True
        assert (await client.get(f"/api/code-review/attempts/{stale.id}")).status_code == 200


async def test_report_saved_and_other_users_404(client, sign_in, db_session):
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, "graded", passed=True)
    url = f"/api/code-review/attempts/{row.id}/report"
    resp = await client.post(url, json={"text": "Судья ошибся", "section": "sql-format"})
    assert resp.status_code == 204 and resp.content == b""
    await client.post(url, json={"text": "Без раздела"})
    reports = (
        await db_session.scalars(
            select(ReviewFeedbackReport).order_by(ReviewFeedbackReport.created_at)
        )
    ).all()
    assert [(r.text, r.section, r.attempt_id, r.user_id) for r in reports] == [
        ("Судья ошибся", "sql-format", row.id, user.id),
        ("Без раздела", None, row.id, user.id),
    ]
    await sign_in("bob")
    assert (await client.post(url, json={"text": "чужая"})).status_code == 404
    assert len((await db_session.scalars(select(ReviewFeedbackReport))).all()) == 2


@pytest.mark.parametrize(
    "body",
    [{"text": ""}, {"text": "я" * 2001}, {"text": "ok", "section": "я" * 201}, {}],
)
async def test_report_validation(client, sign_in, db_session, body):
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, "graded", passed=True)
    resp = await client.post(f"/api/code-review/attempts/{row.id}/report", json=body)
    assert resp.status_code == 422
    assert (await db_session.scalars(select(ReviewFeedbackReport))).all() == []


async def test_report_limits_accepted(client, sign_in, db_session):
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, "graded", passed=True)
    body = {"text": "я" * 2000, "section": "я" * 200}
    assert (
        await client.post(f"/api/code-review/attempts/{row.id}/report", json=body)
    ).status_code == 204


@pytest.mark.parametrize("status", ["draft", "grading", "failed"])
async def test_report_only_for_graded(client, sign_in, db_session, status):
    user = await sign_in("alice")
    row = await add_attempt(db_session, user, status)
    row.submitted_at = datetime.now(UTC)
    await db_session.commit()
    resp = await client.post(f"/api/code-review/attempts/{row.id}/report", json={"text": "x"})
    assert resp.status_code == 409
    assert (await db_session.scalars(select(ReviewFeedbackReport))).all() == []
