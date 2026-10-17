import io
import json
import logging

import pytest
from dishka import Provider, Scope, provide
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.core.logging import JsonFormatter
from app.factory import create_app


async def test_health_ok(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_health_reports_db_down(settings):
    class BrokenSession:
        async def execute(self, *a, **kw):
            raise OSError("db down")

    class Broken(Provider):
        @provide(scope=Scope.REQUEST, override=True)
        def session(self) -> AsyncSession:
            return BrokenSession()  # type: ignore[return-value]

    app = create_app(settings, Broken())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        r = await c.get("/api/health")
    assert r.status_code == 503
    assert r.json() == {"detail": "Database unavailable"}


async def test_domain_error_maps_to_status(app, client):
    async def boom():
        raise NotFound("Lesson not found")

    app.add_api_route("/api/_test/boom", boom)
    r = await client.get("/api/_test/boom")
    assert r.status_code == 404
    assert r.json() == {"detail": "Lesson not found"}


async def test_unexpected_error_is_generic_500(app, client, caplog):
    async def crash():
        raise RuntimeError("secret internals")

    app.add_api_route("/api/_test/crash", crash)
    r = await client.get("/api/_test/crash")
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal Server Error"}
    assert "secret internals" in caplog.text


async def test_unexpected_error_is_logged_as_json_with_request_id(app, client):
    async def crash():
        raise RuntimeError("secret internals")

    app.add_api_route("/api/_test/crash", crash)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logging.getLogger().addHandler(handler)
    try:
        r = await client.get("/api/_test/crash", headers={"X-Request-ID": "rid-1"})
    finally:
        logging.getLogger().removeHandler(handler)
    assert r.headers["x-request-id"] == "rid-1"
    entry = json.loads(stream.getvalue().splitlines()[-1])
    assert set(entry) == {"ts", "level", "logger", "msg", "request_id", "exc_info"}
    assert entry["level"] == "ERROR"
    assert entry["request_id"] == "rid-1"
    assert "secret internals" in entry["exc_info"]


async def test_request_id_is_echoed_or_generated(client):
    r = await client.get("/api/health", headers={"X-Request-ID": "abc"})
    assert r.headers["x-request-id"] == "abc"
    assert len((await client.get("/api/health")).headers["x-request-id"]) == 32


@pytest.mark.parametrize("origin", [None, "", "https://evil.example"])
async def test_mutation_with_wrong_origin_is_403(client, origin):
    headers = {} if origin is None else {"Origin": origin}
    client.headers.pop("Origin")
    r = await client.post("/api/health", headers=headers)
    assert r.status_code == 403
    assert r.json() == {"detail": "Origin not allowed"}


async def test_mutation_with_app_origin_passes_check(client):
    assert (await client.post("/api/health")).status_code == 405  # reaches routing


async def test_get_without_origin_is_allowed(client):
    client.headers.pop("Origin")
    assert (await client.get("/api/health")).status_code == 200
