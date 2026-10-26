from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.evals.service import GradersIn, RunOut

MAX_REVIEW_CHARS = 20_000
SECTION_NAMES = ("Цель", "Контекст", "Формат вывода", "Примеры", "Граничные случаи")
SEVERITIES = ("high", "medium", "low")


class ReviewIn(BaseModel):
    prompt_version_id: UUID | None = None
    system: str | None = None
    user_template: str | None = None

    @model_validator(mode="after")
    def check_source(self) -> "ReviewIn":
        text = (self.system or "") + (self.user_template or "")
        if self.prompt_version_id is not None:
            if self.system is not None or self.user_template is not None:
                raise ValueError("нужна версия промпта или текст, но не оба сразу")
        elif not text.strip():
            raise ValueError("нужна версия промпта или текст")
        if len(text) > MAX_REVIEW_CHARS:
            raise ValueError(
                f"system и user_template вместе не длиннее {MAX_REVIEW_CHARS} символов"
            )
        if "\x00" in text:  # Postgres text cannot hold NUL, it would be a 500 on insert
            raise ValueError("символ NUL не допускается")
        return self


class Section(BaseModel):
    name: Literal[*SECTION_NAMES]  # type: ignore[valid-type]
    score: int = Field(ge=1, le=5)
    comment: str


class Issue(BaseModel):
    severity: Literal[*SEVERITIES]  # type: ignore[valid-type]
    text: str


class Rewritten(BaseModel):
    system: str
    user_template: str


class CriticResult(BaseModel):
    sections: list[Section]
    issues: list[Issue]
    rewritten: Rewritten


class ReviewOut(CriticResult):
    id: UUID
    prompt_id: UUID
    prompt_version_id: UUID
    rewritten_version_id: UUID | None
    variables_changed: bool
    cost_usd: Decimal
    created_at: datetime


class CheckIn(GradersIn):
    dataset_id: UUID


class CheckOut(BaseModel):
    run_a: RunOut
    run_b: RunOut
