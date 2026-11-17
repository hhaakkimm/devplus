import time
from datetime import timedelta

import pytest
from conftest import sign_init_data
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import NotFound
from app.modules.auth.models import User
from app.modules.auth.service import AuthService, TelegramLogin

TOKEN = "123:abc"
TG_ID = 42


@pytest.fixture
def settings(settings: Settings) -> Settings:
    return settings.model_copy(update={"telegram_bot_token": TOKEN})


def init_data(token: str = TOKEN, age: timedelta = timedelta(minutes=1)) -> str:
    user = {"id": TG_ID, "first_name": "Ann"}
    return sign_init_data(token, user, int(time.time() - age.total_seconds()))


async def link(db_session: AsyncSession, login: str, telegram_id: int = TG_ID) -> None:
    db_session.add(User(github_id=1, login=login, name=login.title(), telegram_id=telegram_id))
    await db_session.commit()


async def test_login_sets_session_for_linked_user(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await link(db_session, "alice")
    resp = await client.post("/api/auth/telegram", json={"init_data": init_data()})
    assert resp.status_code == 200
    assert resp.json()["login"] == "alice"
    assert "session" in resp.cookies
    assert "HttpOnly" in resp.headers["set-cookie"]
    me = await client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["login"] == "alice"


async def test_bad_signature_401(client: AsyncClient, db_session: AsyncSession) -> None:
    await link(db_session, "alice")
    resp = await client.post("/api/auth/telegram", json={"init_data": init_data("999:other")})
    assert resp.status_code == 401
    assert "session" not in resp.cookies


async def test_stale_init_data_401(client: AsyncClient, db_session: AsyncSession) -> None:
    await link(db_session, "alice")
    resp = await client.post(
        "/api/auth/telegram", json={"init_data": init_data(age=timedelta(hours=2))}
    )
    assert resp.status_code == 401


async def test_unlinked_telegram_404(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/telegram", json={"init_data": init_data()})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Telegram not linked"}


async def test_linked_user_outside_allowlist_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await link(db_session, "mallory")
    resp = await client.post("/api/auth/telegram", json={"init_data": init_data()})
    assert resp.status_code == 403
    assert "session" not in resp.cookies


async def test_unconfigured_token_404(client: AsyncClient, settings: Settings) -> None:
    settings.telegram_bot_token = ""
    # signed with the empty token, so anyone could forge it: it must not even be checked
    resp = await client.post("/api/auth/telegram", json={"init_data": init_data("")})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Telegram login is not configured"}


async def test_verify_unconfigured_404_even_called_directly(
    db_session: AsyncSession, settings: Settings
) -> None:
    unconfigured = settings.model_copy(update={"telegram_bot_token": ""})
    login = TelegramLogin(AuthService(db_session, unconfigured), unconfigured)
    with pytest.raises(NotFound, match="not configured"):
        login.verify(init_data(""))
