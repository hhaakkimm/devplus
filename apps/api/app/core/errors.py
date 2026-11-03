import json
import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from app.core.logging import request_id_var

logger = logging.getLogger(__name__)


class DomainError(Exception):
    status_code: int = 400


class BadRequest(DomainError):
    status_code = 400


class Unauthorized(DomainError):
    status_code = 401


class Forbidden(DomainError):
    status_code = 403


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    status_code = 409


class Unprocessable(DomainError):
    status_code = 422


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> Response:
        # FastAPI's own handler echoes every input, and NaN, Infinity or a lone surrogate parse
        # as JSON but do not render back: the 422 became a 500. The input stays out, the rest
        # is escaped to ASCII
        errors = [{k: v for k, v in e.items() if k != "input"} for e in exc.errors()]
        body = json.dumps({"detail": jsonable_encoder(errors)}, ensure_ascii=True)
        return Response(body, status_code=422, media_type="application/json")

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        # this response bypasses the request id middleware, so set the header here
        headers = {"X-Request-ID": request_id_var.get() or ""}
        return JSONResponse({"detail": "Internal Server Error"}, status_code=500, headers=headers)
