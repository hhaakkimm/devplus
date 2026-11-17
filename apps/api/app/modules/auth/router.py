import secrets
from dataclasses import asdict

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from app.core.config import Settings
from app.core.errors import BadRequest
from app.modules.auth.schemas import MeOut, TelegramInitIn
from app.modules.auth.service import (
    SESSION_COOKIE,
    SESSION_TTL,
    STATE_COOKIE,
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


@router.get("/me")
async def me(user: FromDishka[CurrentUser]) -> MeOut:
    return MeOut(**asdict(user))


@router.get("/auth/github/login")
async def github_login(login: FromDishka[GitHubLogin], settings: FromDishka[Settings]) -> Response:
    state = secrets.token_urlsafe(16)
    response = RedirectResponse(login.authorize_url(state), status_code=302)
    response.set_cookie(
        STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/auth",
    )
    return response


@router.get("/auth/github/callback")
async def github_callback(
    request: Request,
    login: FromDishka[GitHubLogin],
    settings: FromDishka[Settings],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> Response:
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
    token = await login.complete_login(code)
    response = RedirectResponse("/" if token else "/no-access", status_code=302)
    response.delete_cookie(
        STATE_COOKIE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/auth",
    )
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
