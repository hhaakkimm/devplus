from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quiz.models import QuizAttempt, QuizResult

RECENT_ATTEMPTS = 3


@dataclass(frozen=True)
class QuizAttemptRow:
    score: int
    total: int
    created_at: datetime


@dataclass(frozen=True)
class QuizResultRow:
    quiz_slug: str
    best_score: int
    total: int
    attempts: int
    updated_at: datetime


class QuizService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_results(self, user_id: UUID) -> list[QuizResultRow]:
        rows = await self.session.execute(
            select(
                QuizResult.quiz_slug,
                QuizResult.best_score,
                QuizResult.total,
                QuizResult.attempts,
                QuizResult.updated_at,
            )
            .where(QuizResult.user_id == user_id)
            .order_by(QuizResult.quiz_slug)
        )
        return [QuizResultRow(*row) for row in rows]

    async def recent_attempts(self, user_id: UUID, quiz_slug: str) -> list[QuizAttemptRow]:
        rows = await self.session.execute(
            select(QuizAttempt.score, QuizAttempt.total, QuizAttempt.created_at)
            .where(QuizAttempt.user_id == user_id, QuizAttempt.quiz_slug == quiz_slug)
            .order_by(QuizAttempt.id.desc())
            .limit(RECENT_ATTEMPTS)
        )
        return [QuizAttemptRow(*row) for row in rows]

    async def record(self, user_id: UUID, quiz_slug: str, score: int, total: int) -> None:
        # same transaction as the best-result upsert below: the history cannot drift from `attempts`
        self.session.add(
            QuizAttempt(user_id=user_id, quiz_slug=quiz_slug, score=score, total=total)
        )
        stmt = insert(QuizResult).values(
            user_id=user_id, quiz_slug=quiz_slug, best_score=score, total=total
        )
        new = stmt.excluded
        old = QuizResult
        # compare shares by cross-multiplying (no division); a tie keeps the earlier attempt
        better = new.best_score * old.total > old.best_score * new.total
        # one statement: parallel sends cannot lose an attempt count
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[QuizResult.user_id, QuizResult.quiz_slug],
                set_={
                    "best_score": case((better, new.best_score), else_=old.best_score),
                    "total": case((better, new.total), else_=old.total),
                    "attempts": old.attempts + 1,
                    "updated_at": func.now(),
                },
            )
        )
        await self.session.commit()
