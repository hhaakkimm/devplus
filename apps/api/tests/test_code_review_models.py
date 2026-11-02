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
