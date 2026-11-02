from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

STATUSES = ("draft", "grading", "graded", "failed")


# string FKs: code_review must not import the models of auth
class ReviewAttempt(Base):
    __tablename__ = "review_attempts"
    __table_args__ = (Index("ix_review_attempts_user_id_task_key", "user_id", "task_key"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    task_key: Mapped[str]
    status: Mapped[str]  # one of STATUSES; no DB enum
    comments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), default=list
    )
    verdict: Mapped[str | None]
    summary: Mapped[str | None]
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    cost_usd: Mapped[Decimal | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewFeedbackReport(Base):
    __tablename__ = "review_feedback_reports"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    attempt_id: Mapped[UUID] = mapped_column(ForeignKey("review_attempts.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    section: Mapped[str | None]
    text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
