from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.modules.evals.graders import GraderConfig
from app.modules.evals.jsonutil import check_json_schema, json_bytes
from app.modules.evals.pricing import EFFORTS, MODELS

MAX_PROMPT_CHARS = 50_000
MAX_CASE_BYTES = 32 * 1024
MAX_CASES = 1000
MAX_JSONL_BYTES = 5 * 1024 * 1024
MAX_GRADERS = 5

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class VersionIn(BaseModel):
    system: str
    user_template: str
    model: Literal[*MODELS]  # type: ignore[valid-type]
    effort: Literal[*EFFORTS] = "medium"  # type: ignore[valid-type]
    max_tokens: int = Field(1024, ge=1, le=16000)
    output_schema: dict[str, Any] | None = None

    @model_validator(mode="after")
    def check_limits(self) -> "VersionIn":
        if len(self.system) + len(self.user_template) > MAX_PROMPT_CHARS:
            raise ValueError(
                f"system и user_template вместе не длиннее {MAX_PROMPT_CHARS} символов"
            )
        if self.output_schema is not None:
            check_json_schema(self.output_schema, "output_schema")
        return self


class PromptIn(BaseModel):
    name: Name
    version: VersionIn


class PromptPatch(BaseModel):
    name: Name | None = None
    shared: bool | None = None


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prompt_id: UUID
    number: int
    system: str
    user_template: str
    model: str
    effort: str
    max_tokens: int
    output_schema: dict[str, Any] | None
    created_at: datetime


class PromptSummaryOut(BaseModel):
    id: UUID
    name: str
    shared: bool
    owner_login: str
    latest_version: int
    created_at: datetime


class PromptDetailOut(PromptSummaryOut):
    versions: list[VersionOut]


class CaseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variables: dict[str, str]
    expected: str | None = None

    @model_validator(mode="after")
    def check_limits(self) -> "CaseIn":
        if json_bytes(self.model_dump()) > MAX_CASE_BYTES:
            raise ValueError("кейс не больше 32 КБ")
        # Postgres jsonb and text cannot hold NUL, it would be a 500 on insert
        if any(
            "\x00" in t for t in (*self.variables, *self.variables.values(), self.expected or "")
        ):
            raise ValueError("символ NUL не допускается")
        return self


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    variables: dict[str, str]
    expected: str | None


class DatasetIn(BaseModel):
    name: Name


class DatasetPatch(BaseModel):
    name: Name | None = None
    shared: bool | None = None


class DatasetSummaryOut(BaseModel):
    id: UUID
    name: str
    shared: bool
    owner_login: str
    case_count: int
    created_at: datetime


class DatasetDetailOut(DatasetSummaryOut):
    cases: list[CaseOut]


class ImportOut(BaseModel):
    count: int


def _has_nul(value: Any) -> bool:
    match value:
        case str():
            return "\x00" in value
        case dict():
            return any(_has_nul(k) or _has_nul(v) for k, v in value.items())
        case list():
            return any(_has_nul(v) for v in value)
        case _:
            return False


class GradersIn(BaseModel):
    graders: list[GraderConfig] = Field(max_length=MAX_GRADERS)

    @model_validator(mode="after")
    def check_graders(self) -> "GradersIn":
        # graders are stored as jsonb, which cannot hold NUL: it would be a 500 on insert
        if _has_nul([g.model_dump(mode="json") for g in self.graders]):
            raise ValueError("символ NUL не допускается")
        return self


class RunIn(GradersIn):
    prompt_version_id: UUID
    dataset_id: UUID
    # six places are plenty for a limit and keep the value far from numeric's own bounds
    cost_limit_usd: Decimal | None = Field(None, gt=0, decimal_places=6)


class EstimateOut(BaseModel):
    estimated_cost_usd: Decimal
    cost_limit_usd: Decimal


def _only_when_set() -> Any:
    # Trainer results carry just position, score and passed: unset fields drop out of the JSON
    return Field(None, exclude_if=lambda v: v is None)


class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    score: float
    passed: bool
    input_vars: dict[str, str] | None = _only_when_set()
    output: str | None = _only_when_set()
    truncated: bool | None = _only_when_set()
    grades: list[dict[str, Any]] | None = _only_when_set()
    cost_usd: Decimal | None = _only_when_set()
    latency_ms: int | None = _only_when_set()
    error: str | None = _only_when_set()


class RunSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    status: str
    prompt_version_id: UUID
    dataset_id: UUID | None
    cost_usd: Decimal
    cases_total: int
    cases_done: int
    score_avg: float | None
    pass_rate: float | None
    passed: bool | None
    created_at: datetime
    finished_at: datetime | None


class RunOut(RunSummaryOut):
    cost_limit_usd: Decimal
    estimated_cost_usd: Decimal
    error: str | None
    started_at: datetime | None
    latency_p50_ms: int | None = None
    latency_p95_ms: int | None = None
    # None until the run is read; a run that has not started yet reads as []
    results: list[ResultOut] | None = None
