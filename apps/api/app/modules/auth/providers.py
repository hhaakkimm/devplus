from dishka import Provider, Scope, provide
from fastapi import Request

from app.modules.auth.service import SESSION_COOKIE, AuthService, CurrentUser


class AuthProvider(Provider):
    scope = Scope.REQUEST

    auth_service = provide(AuthService)

    @provide
    async def current_user(self, auth: AuthService, request: Request) -> CurrentUser:
        return await auth.current_user(request.cookies.get(SESSION_COOKIE))
