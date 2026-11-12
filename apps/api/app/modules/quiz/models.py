from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class QuizResult(Base):
    __tablename__ = "quiz_results"
    __table_args__ = (CheckConstraint("best_score >= 0 AND best_score <= total AND total >= 1"),)

    # string FK: quiz must not import auth models
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    quiz_slug: Mapped[str] = mapped_column(primary_key=True)
    # the best attempt is stored as a pair: "5 of 15" must never mix two attempts
    best_score: Mapped[int]
    total: Mapped[int]
    attempts: Mapped[int] = mapped_column(default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
