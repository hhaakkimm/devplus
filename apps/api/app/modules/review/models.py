from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


# string FKs: review must not import the models of auth and evals
class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # the prompt of `prompt_version_id`, kept here so that reading a review never needs access to
    # it. The first check of someone else's version moves both into the reviewer's copy of it
    prompt_id: Mapped[UUID] = mapped_column(ForeignKey("prompts.id", ondelete="CASCADE"))
    prompt_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="CASCADE")
    )
    # set at review time for free text, by the first check for an existing version
    rewritten_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="SET NULL")
    )
    # the critic's answer plus `variables_changed`: {sections, issues, rewritten, variables_changed}
    result: Mapped[dict[str, Any]] = mapped_column(JSONB)
    cost_usd: Mapped[Decimal]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
