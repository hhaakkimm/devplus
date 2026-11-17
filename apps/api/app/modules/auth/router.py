import secrets
from dataclasses import asdict

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from app.core.config import Settings
from app.core.errors import BadRequest
from app.modules.auth.schemas import (
    MeOut,
    TelegramInitIn,
    TelegramLinkOut,
    TelegramLinkPendingOut,
    TelegramUserOut,
)
from app.modules.auth.service import (
    LINK_TTL,
    SESSION_COOKIE,
    SESSION_TTL,
    STATE_COOKIE,
    TG_LINK_COOKIE,
    AuthService,
    CurrentUser,
    GitHubLogin,
    TelegramLogin,
)

router = APIRouter(prefix="/api", route_class=DishkaRoute)


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def set_auth_cookie(response: Response, name: str, value: str, settings: Settings) -> None:
    """A short-lived cookie of the login flow, seen only by /api/auth."""
    response.set_cookie(
        name,
        value,
        max_age=int(LINK_TTL.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/auth",
    )


def delete_auth_cookie(response: Response, name: str, settings: Settings) -> None:
    response.delete_cookie(
        name, httponly=True, secure=settings.cookie_secure, samesite="lax", path="/api/auth"
    )


def github_redirect(login: GitHubLogin, settings: Settings) -> Response:
    state = secrets.token_urlsafe(16)
    response = RedirectResponse(login.authorize_url(state), status_code=302)
    set_auth_cookie(response, STATE_COOKIE, state, settings)
    return response


def link_failed(exc: BadRequest, settings: Settings) -> Response:
    # a fixed code, never the error text, goes into the URL
    reason = "not_allowed" if str(exc) == "not_allowed" else "invalid"
    response = RedirectResponse(f"/tg/link-failed?reason={reason}", status_code=302)
    delete_auth_cookie(response, TG_LINK_COOKIE, settings)
    delete_auth_cookie(response, STATE_COOKIE, settings)
    return response


def oauth_code(request: Request, code: str | None, state: str | None, error: str | None) -> str:
    expected = request.cookies.get(STATE_COOKIE)
    # bytes: compare_digest raises TypeError on non-ASCII str
    if (
        error
        or not code
        or not state
        or not expected
        or not secrets.compare_digest(state.encode(), expected.encode())
    ):
        raise BadRequest("Invalid OAuth callback")
    return code


@router.get("/me")
async def me(user: FromDishka[CurrentUser]) -> MeOut:
    return MeOut(**asdict(user))


@router.get("/auth/github/login")
async def github_login(login: FromDishka[GitHubLogin], settings: FromDishka[Settings]) -> Response:
    return github_redirect(login, settings)


@router.get("/auth/github/callback")
async def github_callback(
    request: Request,
    login: FromDishka[GitHubLogin],
    settings: FromDishka[Settings],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> Response:
    link_token = request.cookies.get(TG_LINK_COOKIE)
    if link_token:
        # linking Telegram: no session here, the person confirms on /tg/confirm
        try:
            secret = await login.complete_link(oauth_code(request, code, state, error), link_token)
        except BadRequest as exc:
            return link_failed(exc, settings)
        response = RedirectResponse("/tg/confirm", status_code=302)
        set_auth_cookie(response, TG_LINK_COOKIE, secret, settings)
        delete_auth_cookie(response, STATE_COOKIE, settings)
        return response
    token = await login.complete_login(oauth_code(request, code, state, error))
    response = RedirectResponse("/" if token else "/no-access", status_code=302)
    delete_auth_cookie(response, STATE_COOKIE, settings)
    if token:
        set_session_cookie(response, token, settings)
    return response


@router.post("/auth/telegram")
async def telegram_login(
    body: TelegramInitIn,
    response: Response,
    login: FromDishka[TelegramLogin],
    settings: FromDishka[Settings],
) -> MeOut:
    token, user = await login.login(body.init_data)
    set_session_cookie(response, token, settings)
    return MeOut(**asdict(user))


@router.post("/auth/telegram/link-start")
async def telegram_link_start(
    body: TelegramInitIn, login: FromDishka[TelegramLogin]
) -> TelegramLinkOut:
    return TelegramLinkOut(url=await login.start_link(body.init_data))


@router.get("/auth/telegram/link")
async def telegram_link(
    login: FromDishka[TelegramLogin],
    github: FromDishka[GitHubLogin],
    settings: FromDishka[Settings],
    token: str = "",
) -> Response:
    try:
        await login.open_link(token)
    except BadRequest as exc:
        return link_failed(exc, settings)
    response = github_redirect(github, settings)
    set_auth_cookie(response, TG_LINK_COOKIE, token, settings)
    return response


@router.get("/auth/telegram/link/pending")
async def telegram_link_pending(
    request: Request, login: FromDishka[TelegramLogin]
) -> TelegramLinkPendingOut:
    p = await login.pending(request.cookies.get(TG_LINK_COOKIE, ""))
    tg = TelegramUserOut(id=p.telegram_id, first_name=p.first_name, username=p.username)
    return TelegramLinkPendingOut(telegram=tg, login=p.login)


@router.post("/auth/telegram/link/confirm", status_code=204)
async def telegram_link_confirm(
    request: Request,
    response: Response,
    login: FromDishka[TelegramLogin],
    settings: FromDishka[Settings],
) -> None:
    await login.confirm(request.cookies.get(TG_LINK_COOKIE, ""))
    delete_auth_cookie(response, TG_LINK_COOKIE, settings)


@router.post("/auth/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    auth: FromDishka[AuthService],
    settings: FromDishka[Settings],
) -> None:
    await auth.logout(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
