from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.code_review.judge import ReviewResult
from app.modules.code_review.tasks import Trap

MAX_COMMENTS = 50
MAX_COMMENT_CHARS = 2000
MAX_SUMMARY_CHARS = 4000


class CommentIn(BaseModel):
    file: str
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    text: str = Field(max_length=MAX_COMMENT_CHARS)


class DraftIn(BaseModel):
    comments: list[CommentIn] = Field(max_length=MAX_COMMENTS)
    verdict: Literal["approve", "request_changes"] | None = None
    summary: str | None = Field(None, max_length=MAX_SUMMARY_CHARS)


class TaskListOut(BaseModel):
    module: str
    slug: str
    title: str
    difficulty: str
    estimate_min: int
    status: Literal["not_started", "attempted", "passed"]


class TaskOut(BaseModel):
    """Only what the student may see: no issues, traps, notes, verdict or reference."""

    module: str
    slug: str
    title: str
    difficulty: str
    estimate_min: int
    statement: str
    files: dict[str, str]


class RevealedIssue(BaseModel):
    id: str
    file: str
    lines: tuple[int, int]
    critical: bool
    description: str
    found: bool
    score: int
    reason: str


class Revealed(BaseModel):
    """The hidden part of a task, shown only for a graded attempt; the judge's notes stay out."""

    issues: list[RevealedIssue]
    traps: list[Trap]
    expected_verdict: Literal["approve", "request_changes"]


class AttemptOut(BaseModel):
    id: UUID
    task_key: str
    status: str
    comments: list[CommentIn]
    verdict: str | None
    summary: str | None
    result: ReviewResult | None
    revealed: Revealed | None
    submitted_at: datetime | None
    created_at: datetime
