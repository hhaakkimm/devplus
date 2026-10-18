from datetime import timedelta

from sqlalchemy import func, select, update

from app.modules.auth.github import GitHubUser
from app.modules.auth.models import User, UserSession
from app.modules.auth.service import AuthService, hash_token


def test_allowlist_is_trimmed_and_case_insensitive(settings):
    assert settings.allowed_logins == frozenset({"alice", "bob"})
    assert settings.model_copy(update={"allowed_github_logins": ""}).allowed_logins == frozenset()


async def test_me_requires_session(client):
    r = await client.get("/api/me")
    assert r.status_code == 401
    assert r.json() == {"detail": "Not authenticated"}


async def test_me_returns_current_user(client, sign_in):
    user = await sign_in("alice")
    r = await client.get("/api/me")
    assert r.status_code == 200
    assert r.json() == {"id": str(user.id), "login": "alice", "name": "Alice", "avatar_url": None}


async def test_unknown_token_is_401(client):
    client.cookies.set("session", "nope")
    assert (await client.get("/api/me")).status_code == 401


async def test_expired_session_is_401(client, sign_in, db_session):
    await sign_in("alice")
    await db_session.execute(
        update(UserSession).values(expires_at=func.now() - timedelta(seconds=1))
    )
    assert (await client.get("/api/me")).status_code == 401


async def test_login_removed_from_allowlist_is_403(client, sign_in):
    await sign_in("carol")  # sign_in bypasses the allowlist, like a session created before removal
    r = await client.get("/api/me")
    assert r.status_code == 403
    assert r.json() == {"detail": "Access revoked"}


async def test_db_stores_only_token_hash(client, sign_in, db_session):
    await sign_in("alice")
    token = client.cookies["session"]
    stored = (await db_session.scalars(select(UserSession.token_hash))).one()
    assert stored == hash_token(token) != token


async def test_upsert_keeps_one_row_per_github_id(db_session, settings):
    auth = AuthService(db_session, settings)
    await auth.upsert_user(GitHubUser(id=1, login="alice", name="A", avatar_url=None))
    user = await auth.upsert_user(
        GitHubUser(id=1, login="alice2", name="B", avatar_url="https://x/a.png")
    )
    assert (user.login, user.name, user.avatar_url) == ("alice2", "B", "https://x/a.png")
    assert await db_session.scalar(select(func.count()).select_from(User)) == 1


async def test_logout_ends_session(client, sign_in, db_session):
    await sign_in("alice")
    r = await client.post("/api/auth/logout")
    assert r.status_code == 204
    assert "Max-Age=0" in r.headers["set-cookie"]
    assert await db_session.scalar(select(func.count()).select_from(UserSession)) == 0
    assert (await client.get("/api/me")).status_code == 401


async def test_logout_with_foreign_origin_keeps_session(client, sign_in):
    await sign_in("alice")
    r = await client.post("/api/auth/logout", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert (await client.get("/api/me")).status_code == 200
