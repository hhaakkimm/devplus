from datetime import datetime
from decimal import Decimal
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
    # none_as_null: Python None is stored as SQL NULL, not as the JSON value `null`
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str]
    shared: Mapped[bool] = mapped_column(server_default=sa.false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DatasetCase(Base):
    __tablename__ = "dataset_cases"
    __table_args__ = (UniqueConstraint("dataset_id", "position"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    position: Mapped[int]
    variables: Mapped[dict[str, str]] = mapped_column(JSONB)
    expected: Mapped[str | None]


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    prompt_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="CASCADE")
    )
    # null for Trainer and review runs: their cases are not a dataset
    dataset_id: Mapped[UUID | None] = mapped_column(ForeignKey("datasets.id", ondelete="SET NULL"))
    source: Mapped[str]  # lab | review | trainer
    task_slug: Mapped[str | None]
    graders: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    # snapshot taken at creation, [{position, variables, expected}]: the worker reads only this,
    # so editing the dataset later cannot break a queued run. Trainer cases stay hidden here.
    cases: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    status: Mapped[str]  # queued | running | done | failed | over_budget
    cost_limit_usd: Mapped[Decimal]
    estimated_cost_usd: Mapped[Decimal]
    cost_usd: Mapped[Decimal] = mapped_column(server_default=sa.text("0"))
    cases_total: Mapped[int]
    cases_done: Mapped[int] = mapped_column(server_default=sa.text("0"))
    score_avg: Mapped[Decimal | None]
    pass_rate: Mapped[Decimal | None]
    passed: Mapped[bool | None]
    error: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RunResult(Base):
    __tablename__ = "run_results"
    __table_args__ = (UniqueConstraint("run_id", "position"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    position: Mapped[int]
    input_vars: Mapped[dict[str, str]] = mapped_column(JSONB)
    output: Mapped[str]
    output_json: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True))
    truncated: Mapped[bool]
    grades: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    score: Mapped[Decimal]
    passed: Mapped[bool]
    input_tokens: Mapped[int]
    output_tokens: Mapped[int]
    cache_read_tokens: Mapped[int]
    cost_usd: Mapped[Decimal]
    latency_ms: Mapped[int]
    error: Mapped[str | None]
