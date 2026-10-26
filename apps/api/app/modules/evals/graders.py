import asyncio
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Annotated, Any, Literal

import regex
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.evals.jsonutil import check_json_schema
from app.modules.evals.llm import LLMClient
from app.modules.evals.pricing import MODELS
from app.modules.evals.safety import check_grader_schema, check_regex, schema_validator

MAX_RUBRIC_SECTIONS = 10


class _Config(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExactGrader(_Config):
    type: Literal["exact"]
    ignore_case: bool = False


class RegexGrader(_Config):
    type: Literal["regex"]
    pattern: str
    must_match: bool = True

    @field_validator("pattern")
    @classmethod
    def check_pattern(cls, v: str) -> str:
        check_regex(v)
        return v


class JsonSchemaGrader(_Config):
    # "schema" would shadow BaseModel.schema; dump under the alias so a stored config re-validates
    model_config = ConfigDict(serialize_by_alias=True)

    type: Literal["json_schema"]
    schema_: dict[str, Any] = Field(alias="schema")

    @field_validator("schema_")
    @classmethod
    def check_schema(cls, v: dict[str, Any]) -> dict[str, Any]:
        check_grader_schema(v)  # first: it bounds the depth the other checks recurse into
        check_json_schema(v, "schema")
        return v


class RubricSection(_Config):
    name: str
    description: str
    weight: float = Field(1, gt=0, le=100)  # inf would make the score NaN


class LlmJudgeGrader(_Config):
    type: Literal["llm_judge"]
    rubric: list[RubricSection] = Field(min_length=1, max_length=MAX_RUBRIC_SECTIONS)
    threshold: float = Field(0.7, ge=0, le=1)
    model: Literal[*MODELS] = "claude-sonnet-5-5"  # type: ignore[valid-type]

    @model_validator(mode="after")
    def check_unique_names(self) -> "LlmJudgeGrader":
        if len({s.name for s in self.rubric}) != len(self.rubric):
            raise ValueError("названия разделов рубрики не повторяются")
        return self


GraderConfig = Annotated[
    ExactGrader | RegexGrader | JsonSchemaGrader | LlmJudgeGrader, Field(discriminator="type")
]


@dataclass
class Grade:
    type: str
    score: float
    passed: bool
    skipped: bool = False
    error: str | None = None
    sections: list[dict[str, Any]] | None = None
    comment: str | None = None
    cost_usd: Decimal = Decimal(0)

    def to_json(self) -> dict[str, Any]:
        # Decimal is not JSON; the string form keeps the exact amount
        return {**asdict(self), "cost_usd": format(self.cost_usd, "f")}


def _scored(type_: str, ok: bool) -> Grade:
    return Grade(type_, float(ok), ok)


def _schema_valid(schema: dict[str, Any], output: str) -> bool:
    # built here, not by the caller: the validator's 1 s regex budget starts when it is created
    try:
        return schema_validator(schema).is_valid(json.loads(output))
    except (ValueError, RecursionError):  # not JSON, or nested too deep to handle
        return False


async def grade(
    cfg: ExactGrader | RegexGrader | JsonSchemaGrader | LlmJudgeGrader,
    *,
    inputs: dict[str, str],
    expected: str | None,
    output: str,
    llm: LLMClient,
) -> Grade:
    match cfg:
        case ExactGrader():
            if expected is None:
                return Grade("exact", 0.0, False, skipped=True)
            a, b = output.strip(), expected.strip()
            return _scored("exact", a.casefold() == b.casefold() if cfg.ignore_case else a == b)
        case RegexGrader():
            # in a thread (`regex` lets go of the GIL on a str): a pattern that burns its whole
            # second must not freeze the other cases of the run
            try:
                found = await asyncio.to_thread(regex.search, cfg.pattern, output, timeout=1.0)
            except TimeoutError:
                return Grade("regex", 0.0, False, error="Таймаут регулярного выражения")
            return _scored("regex", (found is not None) == cfg.must_match)
        case JsonSchemaGrader():
            try:
                ok = await asyncio.to_thread(_schema_valid, cfg.schema_, output)
            except TimeoutError:
                return Grade("json_schema", 0.0, False, error="Таймаут регулярного выражения")
            return _scored("json_schema", ok)
        case LlmJudgeGrader():
            # judge.py builds Grades, so it imports this module; import it here to avoid a cycle
            from app.modules.evals.judge import judge

            return await judge(llm, cfg, inputs, expected, output)


def case_result(grades: list[Grade]) -> tuple[float, bool]:
    scored = [g for g in grades if not g.skipped]
    if not scored:
        return 0.0, False
    return sum(g.score for g in scored) / len(scored), all(g.passed for g in scored)
