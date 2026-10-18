from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# evals must not import auth models: FKs are strings, and this stub only reads user logins
users = sa.table("users", sa.column("id", sa.Uuid), sa.column("login", sa.String))


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str]
    shared: Mapped[bool] = mapped_column(server_default=sa.false())
    # set for Trainer task prompts: private to the owner and never listed in the Lab
    trainer_task: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("prompt_id", "number"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    prompt_id: Mapped[UUID] = mapped_column(ForeignKey("prompts.id", ondelete="CASCADE"))
    number: Mapped[int]
    system: Mapped[str]
    user_template: Mapped[str]
    model: Mapped[str]
    effort: Mapped[str]
    max_tokens: Mapped[int]
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
