from collections.abc import AsyncIterator

import httpx
from dishka import Provider, Scope, provide
from fastapi import Request

from app.modules.auth.github import GitHubClient, HttpGitHubClient
from app.modules.auth.service import (
    SESSION_COOKIE,
    AuthService,
    CurrentUser,
    GitHubLogin,
    TelegramLogin,
)


class AuthProvider(Provider):
    scope = Scope.REQUEST

    auth_service = provide(AuthService)
    github_login = provide(GitHubLogin)
    telegram_login = provide(TelegramLogin)
    github_client = provide(HttpGitHubClient, scope=Scope.APP, provides=GitHubClient)

    @provide(scope=Scope.APP)
    async def http_client(self) -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient() as http:
            yield http

    @provide
    async def current_user(self, auth: AuthService, request: Request) -> CurrentUser:
        return await auth.current_user(request.cookies.get(SESSION_COOKIE))
