from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class _OriginCheckMiddleware:
    def __init__(self, app: ASGIApp, app_origin: str) -> None:
        self.app = app
        self.app_origin = app_origin

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope["method"] in _MUTATING_METHODS
            and Headers(scope=scope).get("origin") != self.app_origin
        ):
            response = JSONResponse({"detail": "Origin not allowed"}, status_code=403)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def install_origin_check(app: FastAPI, app_origin: str) -> None:
    app.add_middleware(_OriginCheckMiddleware, app_origin=app_origin)
