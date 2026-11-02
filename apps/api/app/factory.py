from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka import Provider
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from app.core.config import Settings
from app.core.container import build_container
from app.core.errors import register_error_handlers
from app.core.health import router as health_router
from app.core.logging import install_request_id
from app.core.security import install_origin_check
from app.modules.auth.router import router as auth_router
from app.modules.code_review.router import router as code_review_router
from app.modules.evals.router import router as evals_router
from app.modules.progress.router import router as progress_router
from app.modules.review.router import router as review_router
from app.modules.simulator.router import router as simulator_router
from app.modules.trainer.router import router as trainer_router


def create_app(settings: Settings | None = None, *overrides: Provider) -> FastAPI:
    settings = settings or Settings()
    container = build_container(settings, *overrides)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await container.close()

    app = FastAPI(lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(progress_router)
    app.include_router(evals_router)
    app.include_router(review_router)
    app.include_router(trainer_router)
    app.include_router(code_review_router)
    app.include_router(simulator_router)
    register_error_handlers(app)
    setup_dishka(container, app)
    # added last = outermost, so even 403s from the origin check carry X-Request-ID
    install_origin_check(app, settings.app_origin)
    install_request_id(app)
    return app
