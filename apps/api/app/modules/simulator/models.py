from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


# string FKs: simulator must not import the models of auth
class SimAttempt(Base):
    __tablename__ = "sim_attempts"
    __table_args__ = (
        Index("ix_sim_attempts_user_id_task_key_created_at", "user_id", "task_key", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    task_key: Mapped[str]  # "<module>/<slug>"
    graph: Mapped[dict[str, Any]] = mapped_column(JSONB)
    answers: Mapped[dict[str, str]] = mapped_column(JSONB)  # {requirements, estimates, tradeoffs}
    # every scenario, hidden ones too, with its targets left out; and every rule finding
    scenarios: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    # none_as_null: no review is SQL NULL, not the JSON value `null`
    review: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    review_error: Mapped[str | None]
    score: Mapped[Decimal | None]
    passed: Mapped[bool]
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
