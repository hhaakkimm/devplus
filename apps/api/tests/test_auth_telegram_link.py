import time
from dataclasses import replace
from datetime import timedelta
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlparse

import pytest
from conftest import github_login, sign_init_data
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.factory import create_app
from app.modules.auth.models import TelegramLinkRequest, User, UserSession
from app.modules.auth.service import AuthService, hash_token

TOKEN = "123:abc"
TG_ID = 42
ORIGIN = "http://testserver"
START = "/api/auth/telegram/link-start"
PENDING = "/api/auth/telegram/link/pending"
CONFIRM = "/api/auth/telegram/link/confirm"
SHOWN = {"telegram_id": TG_ID}  # the Telegram that pending showed
TAKEN = {"detail": "Telegram is linked to another account"}
MISMATCH = {"detail": "Telegram does not match the confirmation"}


@pytest.fixture
def settings(settings: Settings) -> Settings:
    return settings.model_copy(update={"telegram_bot_token": TOKEN})


def init_data(bot_token: str = TOKEN, **user: object) -> str:
    user = {"id": TG_ID, "first_name": "Аня", "username": "ann"} | user
    return sign_init_data(bot_token, user, int(time.time()) - 60)


def client_for(app: FastAPI, **cookies: str) -> AsyncClient:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    return AsyncClient(
        transport=transport, base_url=ORIGIN, headers={"Origin": ORIGIN}, cookies=cookies
    )


async def count(db_session: AsyncSession, model: type) -> int:
    return await db_session.scalar(select(func.count()).select_from(model))


async def telegram_ids(db_session: AsyncSession) -> dict[str, int | None]:
    return dict((await db_session.execute(select(User.login, User.telegram_id))).all())


async def no_session(client: AsyncClient, db_session: AsyncSession) -> bool:
    return "session" not in client.cookies and await count(db_session, UserSession) == 0


async def start(client: AsyncClient, **user: object) -> str:
    """link-start from the Mini App, returns the token of the link it gives."""
    r = await client.post(START, json={"init_data": init_data(**user)})
    assert r.status_code == 200
    return parse_qs(urlparse(r.json()["url"]).query)["token"][0]


async def link_through_github(client: AsyncClient, token: str) -> Response:
    await client.get(f"/api/auth/telegram/link?token={token}")
    return await client.get(
        f"/api/auth/github/callback?code=x&state={client.cookies['oauth_state']}"
    )


async def expire_requests(db_session: AsyncSession) -> None:
    await db_session.execute(
        update(TelegramLinkRequest).values(expires_at=func.now() - timedelta(seconds=1))
    )
    await db_session.commit()


async def test_link_start_stores_name_and_returns_url(client, db_session):
    r = await client.post(START, json={"init_data": init_data()})
    assert r.status_code == 200
    assert "set-cookie" not in r.headers
    url = r.json()["url"]
    assert url.startswith(f"{ORIGIN}/api/auth/telegram/link?token=")
    token = parse_qs(urlparse(url).query)["token"][0]
    assert len(token) >= 43
    R = TelegramLinkRequest
    row = (
        await db_session.execute(
            select(
                R.token_hash, R.telegram_id, R.first_name, R.username, R.user_id,
                R.expires_at - func.now(),
            )
        )
    ).one()  # fmt: skip
    assert tuple(row) == (hash_token(token), TG_ID, "Аня", "ann", None, timedelta(minutes=10))


async def test_link_start_bad_signature_401(client, db_session):
    r = await client.post(START, json={"init_data": init_data("999:other")})
    assert r.status_code == 401
    assert await count(db_session, TelegramLinkRequest) == 0


async def test_link_redirects_to_github_with_state_and_sets_tg_link(client):
    token = await start(client)
    r = await client.get(f"/api/auth/telegram/link?token={token}")
    url = urlparse(r.headers["location"])
    assert (r.status_code, url.netloc, url.path) == (302, "github.com", "/login/oauth/authorize")
    assert parse_qs(url.query)["state"] == [client.cookies["oauth_state"]]
    assert client.cookies["tg_link"] == token


async def test_link_cookie_attributes(settings, overrides):
    secure = settings.model_copy(update={"cookie_secure": True})
    async with client_for(create_app(secure, *overrides)) as c:
        token = await start(c)
        r = await c.get(f"/api/auth/telegram/link?token={token}")
    jar = SimpleCookie()
    for header in r.headers.get_list("set-cookie"):
        jar.load(header)
    m = jar["tg_link"]
    attrs = (bool(m["httponly"]), bool(m["secure"]), m["samesite"], m["path"], m["max-age"])
    assert attrs == (True, True, "lax", "/api/auth", "600")


async def test_callback_with_tg_link_sets_user_id_but_not_telegram_id_and_no_session(
    client, db_session
):
    token = await start(client)
    r = await link_through_github(client, token)
    assert (r.status_code, r.headers["location"]) == (302, "/tg/confirm")
    assert await no_session(client, db_session)
    assert await telegram_ids(db_session) == {"alice": None}
    alice = await db_session.scalar(select(User.id).where(User.login == "alice"))
    assert await db_session.scalar(select(TelegramLinkRequest.user_id)) == alice
    assert "oauth_state" not in client.cookies
    # the confirm secret is new: the link token, known to whoever made the link, is spent
    assert client.cookies["tg_link"] != token


async def test_link_token_alone_cannot_see_or_confirm(app, client, db_session):
    """link-start is open to any bot user: the link maker knows the token and may send the link
    to a teammate. After the teammate signs in to GitHub, that token must not confirm."""
    token = await start(client)
    await link_through_github(client, token)
    async with client_for(app, tg_link=token) as maker:
        assert (await maker.get(PENDING)).status_code == 404
        assert (await maker.post(CONFIRM, json=SHOWN)).status_code == 404
    assert await telegram_ids(db_session) == {"alice": None}
    assert (await client.post(CONFIRM, json=SHOWN)).status_code == 204


async def test_pending_returns_telegram_name_and_login(client):
    await link_through_github(client, await start(client))
    r = await client.get(PENDING)
    assert r.status_code == 200
    assert r.json() == {
        "telegram": {"id": TG_ID, "first_name": "Аня", "username": "ann"},
        "login": "alice",
    }


async def test_confirm_links_and_deletes_request(client, db_session):
    await link_through_github(client, await start(client))
    r = await client.post(CONFIRM, json=SHOWN)
    assert r.status_code == 204
    assert "tg_link" not in client.cookies
    assert await telegram_ids(db_session) == {"alice": TG_ID}
    assert await count(db_session, TelegramLinkRequest) == 0
    assert await no_session(client, db_session)
    # the Mini App now signs in by initData alone
    login = await client.post("/api/auth/telegram", json={"init_data": init_data()})
    assert login.json()["login"] == "alice"


async def test_no_confirm_no_link(client, db_session):
    await link_through_github(client, await start(client))
    assert (await client.get(PENDING)).status_code == 200
    assert await telegram_ids(db_session) == {"alice": None}
    login = await client.post("/api/auth/telegram", json={"init_data": init_data()})
    assert login.status_code == 404


async def test_confirm_twice_fails(client, db_session):
    await link_through_github(client, await start(client))
    secret = client.cookies["tg_link"]
    assert (await client.post(CONFIRM, json=SHOWN)).status_code == 204
    client.cookies.set("tg_link", secret)
    assert (await client.post(CONFIRM, json=SHOWN)).status_code == 404
    assert (await client.get(PENDING)).status_code == 404


async def test_confirm_without_tg_link_cookie_fails(client, db_session):
    await link_through_github(client, await start(client))
    client.cookies.delete("tg_link")
    assert (await client.get(PENDING)).status_code == 404
    assert (await client.post(CONFIRM, json=SHOWN)).status_code == 404
    assert await telegram_ids(db_session) == {"alice": None}


async def test_unfinished_github_cannot_confirm(client, db_session):
    token = await start(client)
    await client.get(f"/api/auth/telegram/link?token={token}")
    assert client.cookies["tg_link"] == token
    assert (await client.get(PENDING)).status_code == 404
    assert (await client.post(CONFIRM, json=SHOWN)).status_code == 404
    assert await telegram_ids(db_session) == {}


@pytest.mark.parametrize("expires_before", ["link", "callback"])
async def test_expired_token_redirects_to_link_failed(client, db_session, expires_before):
    token = await start(client)
    if expires_before == "link":
        await expire_requests(db_session)
        r = await client.get(f"/api/auth/telegram/link?token={token}")
    else:
        await client.get(f"/api/auth/telegram/link?token={token}")
        await expire_requests(db_session)
        r = await client.get(
            f"/api/auth/github/callback?code=x&state={client.cookies['oauth_state']}"
        )
    assert (r.status_code, r.headers["location"]) == (302, "/tg/link-failed?reason=invalid")
    assert "tg_link" not in client.cookies
    assert "oauth_state" not in client.cookies
    assert await no_session(client, db_session)
    assert await db_session.scalar(select(TelegramLinkRequest.user_id)) is None


async def test_expired_after_github_cannot_confirm(client, db_session):
    await link_through_github(client, await start(client))
    await expire_requests(db_session)
    assert (await client.get(PENDING)).status_code == 404
    assert (await client.post(CONFIRM, json=SHOWN)).status_code == 404
    assert await telegram_ids(db_session) == {"alice": None}


async def test_unknown_token_redirects_to_link_failed(client):
    r = await client.get("/api/auth/telegram/link?token=nope")
    assert (r.status_code, r.headers["location"]) == (302, "/tg/link-failed?reason=invalid")
    r = await client.get("/api/auth/telegram/link")
    assert (r.status_code, r.headers["location"]) == (302, "/tg/link-failed?reason=invalid")


@pytest.mark.parametrize(
    "query", ["code=x&state=wrong", "state=STATE", "error=access_denied&state=STATE", "code=x"]
)
async def test_bad_oauth_callback_in_link_redirects_to_link_failed(client, db_session, query):
    await client.get(f"/api/auth/telegram/link?token={await start(client)}")
    r = await client.get(
        "/api/auth/github/callback?" + query.replace("STATE", client.cookies["oauth_state"])
    )
    assert (r.status_code, r.headers["location"]) == (302, "/tg/link-failed?reason=invalid")
    assert "tg_link" not in client.cookies
    assert "oauth_state" not in client.cookies
    assert await no_session(client, db_session)
    assert await count(db_session, User) == 0
    assert await db_session.scalar(select(TelegramLinkRequest.user_id)) is None


async def test_confirm_other_telegram_id_400_binds_nothing_and_spends_request(client, db_session):
    await link_through_github(client, await start(client))
    r = await client.post(CONFIRM, json={"telegram_id": 777})
    assert (r.status_code, r.json()) == (400, MISMATCH)
    assert await telegram_ids(db_session) == {"alice": None}
    assert await no_session(client, db_session)
    # a mismatch means the cookie was swapped: its request is spent, no second try
    assert await count(db_session, TelegramLinkRequest) == 0
    assert (await client.post(CONFIRM, json=SHOWN)).status_code == 404


async def test_swapped_link_cookie_confirms_nothing(client, db_session):
    """The confirm page shows link A; an attacker page then sends the same browser through
    link B (GitHub approves at once), which replaces tg_link. The open page confirms A."""
    await link_through_github(client, await start(client))
    shown = (await client.get(PENDING)).json()["telegram"]
    assert shown["id"] == TG_ID
    mallory = await start(client, id=666, first_name="Mallory", username="mallory")
    assert (await link_through_github(client, mallory)).headers["location"] == "/tg/confirm"
    r = await client.post(CONFIRM, json={"telegram_id": shown["id"]})
    assert (r.status_code, r.json()) == (400, MISMATCH)
    assert await telegram_ids(db_session) == {"alice": None}
    assert await no_session(client, db_session)
    # Mallory's request is spent; A's stays bound, but no browser holds its secret any more
    left = await db_session.scalars(select(TelegramLinkRequest.telegram_id))
    assert list(left) == [TG_ID]


@pytest.mark.parametrize("body", [None, {}, {"telegram_id": "x"}])
async def test_confirm_without_valid_body_422_binds_nothing(client, db_session, body):
    await link_through_github(client, await start(client))
    assert (await client.post(CONFIRM, json=body)).status_code == 422
    assert await telegram_ids(db_session) == {"alice": None}
    assert await count(db_session, TelegramLinkRequest) == 1  # still confirmable


async def test_login_outside_allowlist_redirects_to_link_failed_not_allowed_and_deletes_request(
    client, fake_github, db_session
):
    fake_github.user = replace(fake_github.user, id=2, login="mallory")
    r = await link_through_github(client, await start(client))
    assert (r.status_code, r.headers["location"]) == (302, "/tg/link-failed?reason=not_allowed")
    assert await count(db_session, TelegramLinkRequest) == 0
    assert await count(db_session, User) == 0
    assert await no_session(client, db_session)
    assert "tg_link" not in client.cookies
    assert "oauth_state" not in client.cookies


async def test_second_callback_with_same_tg_link_does_not_rebind(client, fake_github, db_session):
    """Pins the `user_id IS NULL` guard of complete_link: the callback binds a request once."""
    token = await start(client)
    await client.get(f"/api/auth/telegram/link?token={token}")
    state = client.cookies["oauth_state"]
    callback = f"/api/auth/github/callback?code=x&state={state}"
    assert (await client.get(callback)).headers["location"] == "/tg/confirm"
    alice = await db_session.scalar(select(User.id).where(User.login == "alice"))
    # the same tg_link (now the confirm secret) goes through GitHub again, as another user
    fake_github.user = replace(fake_github.user, id=2, login="bob")
    client.cookies.set("oauth_state", state, path="/api/auth")
    r = await client.get(callback)
    assert (r.status_code, r.headers["location"]) == (302, "/tg/link-failed?reason=invalid")
    assert await db_session.scalar(select(TelegramLinkRequest.user_id)) == alice
    assert await telegram_ids(db_session) == {"alice": None, "bob": None}


async def test_init_data_over_4096_chars_422(client):
    r = await client.post("/api/auth/telegram", json={"init_data": "x" * 4097})
    assert r.status_code == 422


async def test_telegram_id_taken_by_other_user_400_on_confirm(client, db_session):
    db_session.add(User(github_id=2, login="bob", telegram_id=TG_ID))
    await db_session.commit()
    await link_through_github(client, await start(client))
    r = await client.post(CONFIRM, json=SHOWN)
    assert (r.status_code, r.json()) == (400, TAKEN)
    assert await telegram_ids(db_session) == {"alice": None, "bob": TG_ID}
    assert await count(db_session, TelegramLinkRequest) == 0


async def test_confirm_race_on_telegram_id_is_400_not_500(client, db_session, monkeypatch):
    """Two confirms of one Telegram pass the check together: the unique index decides."""
    db_session.add(User(github_id=2, login="bob", telegram_id=TG_ID))
    await db_session.commit()
    await link_through_github(client, await start(client))

    async def not_yet_taken(self: AuthService, telegram_id: int) -> None:
        return None

    monkeypatch.setattr(AuthService, "user_by_telegram_id", not_yet_taken)
    r = await client.post(CONFIRM, json=SHOWN)
    assert (r.status_code, r.json()) == (400, TAKEN)
    assert await telegram_ids(db_session) == {"alice": None, "bob": TG_ID}
    assert await count(db_session, TelegramLinkRequest) == 0


async def test_relink_replaces_own_telegram_id(client, db_session):
    db_session.add(User(github_id=1, login="alice", telegram_id=111))
    await db_session.commit()
    await link_through_github(client, await start(client))
    assert (await client.post(CONFIRM, json=SHOWN)).status_code == 204
    assert await telegram_ids(db_session) == {"alice": TG_ID}


async def test_expired_requests_are_deleted_on_start(client, db_session):
    R = TelegramLinkRequest
    for token_hash, ttl in [("old", timedelta(seconds=-1)), ("live", timedelta(minutes=5))]:
        db_session.add(
            R(token_hash=token_hash, telegram_id=7, first_name="X", expires_at=func.now() + ttl)
        )
    await db_session.commit()
    token = await start(client)
    hashes = set(await db_session.scalars(select(R.token_hash)))
    assert hashes == {"live", hash_token(token)}


async def test_plain_github_login_unchanged_with_stray_request_row(client, db_session):
    await start(client)  # a request exists, but this browser never opened the link
    r = await github_login(client)
    assert (r.status_code, r.headers["location"]) == (302, "/")
    assert (await client.get("/api/me")).json()["login"] == "alice"
    assert await db_session.scalar(select(TelegramLinkRequest.user_id)) is None
    assert await telegram_ids(db_session) == {"alice": None}


@pytest.mark.parametrize(
    "method, path",
    [
        ("POST", "/api/auth/telegram"),
        ("POST", START),
        ("GET", "/api/auth/telegram/link?token=open"),
        ("GET", PENDING),
        ("POST", CONFIRM),
    ],
)
@pytest.mark.parametrize("with_body", [True, False])
async def test_unconfigured_token_404_on_all_five(
    settings, overrides, db_session, method, path, with_body
):
    alice = User(github_id=1, login="alice")
    db_session.add(alice)
    await db_session.flush()
    # live requests: 404 must come before any lookup, not from a failed one
    for token, user_id in [("open", None), ("done", alice.id)]:
        db_session.add(
            TelegramLinkRequest(
                token_hash=hash_token(token),
                telegram_id=TG_ID,
                first_name="Аня",
                user_id=user_id,
                expires_at=func.now() + timedelta(minutes=5),
            )
        )
    await db_session.commit()
    unconfigured = settings.model_copy(update={"telegram_bot_token": ""})
    async with client_for(create_app(unconfigured, *overrides), tg_link="done") as c:
        # the 404 comes before body validation too: no body is not a 422 here
        body = {"init_data": init_data(""), **SHOWN} if with_body else None
        r = await c.request(method, path, json=body)
    assert (r.status_code, r.json()) == (404, {"detail": "Telegram login is not configured"})
    assert await telegram_ids(db_session) == {"alice": None}
    assert await count(db_session, TelegramLinkRequest) == 2
