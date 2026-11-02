import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.auth.github import GitHubUser
from app.modules.auth.service import AuthService
from app.modules.code_review.models import ReviewAttempt


async def test_attempt_defaults(db_session, settings):
    user = await AuthService(db_session, settings).upsert_user(
        GitHubUser(id=1, login="alice", name="Alice", avatar_url=None)
    )
    attempt = ReviewAttempt(user_id=user.id, task_key="01-x/y", status="draft")
    db_session.add(attempt)
    await db_session.flush()
    await db_session.refresh(attempt)
    assert attempt.comments == []
    assert attempt.created_at is not None
    assert attempt.submitted_at is None


async def test_one_draft_per_user_and_task(db_session, settings):
    auth = AuthService(db_session, settings)
    alice = await auth.upsert_user(GitHubUser(id=1, login="alice", name="Alice", avatar_url=None))
    bob = await auth.upsert_user(GitHubUser(id=2, login="bob", name="Bob", avatar_url=None))

    def attempt(user, key="01-x/y", status="draft"):
        return ReviewAttempt(user_id=user.id, task_key=key, status=status)

    db_session.add_all(
        [attempt(alice), attempt(alice, status="graded"), attempt(alice, status="graded")]
        + [attempt(alice, key="01-x/z"), attempt(bob)]
    )
    await db_session.flush()
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(attempt(alice))
