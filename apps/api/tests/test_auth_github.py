from dataclasses import replace
from http.cookies import Morsel, SimpleCookie
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from conftest import github_login
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select

from app.core.errors import BadRequest
from app.factory import create_app
from app.modules.auth.github import GitHubUser, HttpGitHubClient
from app.modules.auth.models import User, UserSession


async def count(db_session, model) -> int:
    return await db_session.scalar(select(func.count()).select_from(model))


def set_cookies(r: Response) -> dict[str, Morsel]:
    jar = SimpleCookie()
    for header in r.headers.get_list("set-cookie"):
        jar.load(header)
    return dict(jar)


async def test_login_redirects_to_github_with_state(client):
    r = await client.get("/api/auth/github/login")
    assert r.status_code == 302
    url = urlparse(r.headers["location"])
    q = parse_qs(url.query)
    assert (url.netloc, url.path) == ("github.com", "/login/oauth/authorize")
    assert q["client_id"] == ["cid"]
    assert q["redirect_uri"] == ["http://testserver/api/auth/github/callback"]
    assert q["scope"] == ["read:user"]
    assert q["state"] == [client.cookies["oauth_state"]]


async def test_callback_signs_in_allowed_user(client):
    r = await github_login(client)
    assert (r.status_code, r.headers["location"]) == (302, "/")
    assert (await client.get("/api/me")).json()["login"] == "alice"


async def test_repeat_login_updates_profile(client, fake_github, db_session):
    await github_login(client)
    assert (await client.get("/api/me")).json()["name"] == "Alice"
    fake_github.user = replace(fake_github.user, login="Alice", name="Alice Renamed")
    await github_login(client)
    assert await count(db_session, User) == 1
    assert (await client.get("/api/me")).json()["name"] == "Alice Renamed"


async def test_login_outside_allowlist_goes_to_no_access(client, fake_github, db_session):
    fake_github.user = replace(fake_github.user, id=2, login="mallory")
    r = await github_login(client)
    assert r.headers["location"] == "/no-access"
    assert await count(db_session, User) == 0
    assert await count(db_session, UserSession) == 0
    assert "session" not in client.cookies


@pytest.mark.parametrize(
    "query",
    ["code=x&state=wrong", "state=STATE", "error=access_denied&state=STATE", "code=x&state=%C3%A9"],
)
async def test_bad_callback_is_400(client, db_session, query):
    await client.get("/api/auth/github/login")
    r = await client.get(
        "/api/auth/github/callback?" + query.replace("STATE", client.cookies["oauth_state"])
    )
    assert r.status_code == 400
    assert r.json() == {"detail": "Invalid OAuth callback"}
    assert await count(db_session, User) == 0
    assert await count(db_session, UserSession) == 0


async def test_callback_without_state_cookie_is_400(client):
    assert (await client.get("/api/auth/github/callback?code=x&state=s")).status_code == 400


async def test_callback_without_state_param_is_400(client):
    await client.get("/api/auth/github/login")
    assert (await client.get("/api/auth/github/callback?code=x")).status_code == 400


async def test_cookie_attributes(settings, overrides):
    secure = settings.model_copy(update={"cookie_secure": True})
    transport = ASGITransport(app=create_app(secure, *overrides))
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers={"Origin": secure.app_origin}
    ) as c:
        state = set_cookies(await c.get("/api/auth/github/login"))["oauth_state"]
        callback = await c.get(
            f"/api/auth/github/callback?code=x&state={state.value}",
            headers={"Cookie": f"oauth_state={state.value}"},
        )
        logout = await c.post("/api/auth/logout")

    def attrs(m: Morsel) -> tuple:
        return (bool(m["httponly"]), bool(m["secure"]), m["samesite"], m["path"], m["max-age"])

    cb, out = set_cookies(callback), set_cookies(logout)
    assert attrs(state) == (True, True, "lax", "/api/auth", "600")
    assert attrs(cb["session"]) == (True, True, "lax", "/", "2592000")
    assert attrs(cb["oauth_state"]) == (True, True, "lax", "/api/auth", "0")
    assert attrs(out["session"]) == (True, True, "lax", "/", "0")


async def test_http_client_maps_github_error(settings):
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"error": "bad_verification_code"})
    )
    async with httpx.AsyncClient(transport=transport) as http:
        with pytest.raises(BadRequest, match="GitHub login failed"):
            await HttpGitHubClient(http, settings).exchange_code("x")


async def test_http_client_sends_oauth_app_credentials(settings):
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url == "https://github.com/login/oauth/access_token"
        assert req.headers["accept"] == "application/json"
        assert parse_qs(req.content.decode()) == {
            "client_id": ["cid"],
            "client_secret": ["csecret"],
            "code": ["x"],
        }
        return httpx.Response(200, json={"access_token": "t"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        assert await HttpGitHubClient(http, settings).exchange_code("x") == "t"


async def test_http_client_reads_user(settings):
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.headers["authorization"] == "Bearer t"
        return httpx.Response(
            200, json={"id": 7, "login": "alice", "name": None, "avatar_url": "https://a/x.png"}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        user = await HttpGitHubClient(http, settings).get_user("t")
    assert user == GitHubUser(7, "alice", None, "https://a/x.png")


async def test_http_client_maps_user_error(settings):
    transport = httpx.MockTransport(lambda req: httpx.Response(401, json={"message": "Bad"}))
    async with httpx.AsyncClient(transport=transport) as http:
        with pytest.raises(BadRequest, match="GitHub login failed"):
            await HttpGitHubClient(http, settings).get_user("t")
