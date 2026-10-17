import logging

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", route_class=DishkaRoute)


@router.get("/health")
async def health(session: FromDishka[AsyncSession]) -> dict[str, str]:
    try:
        await session.execute(text("select 1"))
    except (OSError, SQLAlchemyError) as exc:
        logger.warning("Health check failed", exc_info=exc)
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok"}
