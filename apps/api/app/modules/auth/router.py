from dataclasses import asdict

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, Response

from app.modules.auth.schemas import MeOut
from app.modules.auth.service import SESSION_COOKIE, AuthService, CurrentUser

router = APIRouter(prefix="/api", route_class=DishkaRoute)


@router.get("/me")
async def me(user: FromDishka[CurrentUser]) -> MeOut:
    return MeOut(**asdict(user))


@router.post("/auth/logout", status_code=204)
async def logout(request: Request, response: Response, auth: FromDishka[AuthService]) -> None:
    await auth.logout(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
