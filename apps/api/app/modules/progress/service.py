from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.progress.models import LessonProgress


@dataclass(frozen=True)
class CompletedLesson:
    lesson_slug: str
    completed_at: datetime


class ProgressService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_completed(self, user_id: UUID) -> list[CompletedLesson]:
        rows = await self.session.execute(
            select(LessonProgress.lesson_slug, LessonProgress.completed_at)
            .where(LessonProgress.user_id == user_id)
            .order_by(LessonProgress.completed_at)
        )
        return [CompletedLesson(*row) for row in rows]

    async def mark_done(self, user_id: UUID, lesson_slug: str) -> None:
        await self.session.execute(
            insert(LessonProgress)
            .values(user_id=user_id, lesson_slug=lesson_slug)
            .on_conflict_do_nothing()
        )
        await self.session.commit()

    async def unmark(self, user_id: UUID, lesson_slug: str) -> None:
        await self.session.execute(
            delete(LessonProgress).where(
                LessonProgress.user_id == user_id, LessonProgress.lesson_slug == lesson_slug
            )
        )
        await self.session.commit()
