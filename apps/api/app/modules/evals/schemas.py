import json
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.modules.evals.pricing import EFFORTS, MODELS

MAX_PROMPT_CHARS = 50_000
MAX_SCHEMA_BYTES = 64 * 1024

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
            if len(json.dumps(self.output_schema).encode()) > MAX_SCHEMA_BYTES:
                raise ValueError("output_schema не больше 64 КБ")
            try:
                Draft202012Validator.check_schema(self.output_schema)
            except SchemaError as e:
                raise ValueError(f"output_schema не JSON Schema: {e.message}") from e
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
