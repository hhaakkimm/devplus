from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.code_review.judge import ReviewResult
from app.modules.code_review.tasks import ReviewTrap

MAX_COMMENTS = 50
MAX_COMMENT_CHARS = 2000
MAX_SUMMARY_CHARS = 4000


class ReviewCommentIn(BaseModel):
    file: str
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    text: str = Field(max_length=MAX_COMMENT_CHARS)


class ReviewDraftIn(BaseModel):
    comments: list[ReviewCommentIn] = Field(max_length=MAX_COMMENTS)
    verdict: Literal["approve", "request_changes"] | None = None
    summary: str | None = Field(None, max_length=MAX_SUMMARY_CHARS)


class ReviewTaskListOut(BaseModel):
    module: str
    slug: str
    title: str
    difficulty: str
    estimate_min: int
    status: Literal["not_started", "attempted", "passed"]


class ReviewTaskOut(BaseModel):
    """Only what the student may see: no issues, traps, notes, verdict or reference."""

    module: str
    slug: str
    title: str
    difficulty: str
    estimate_min: int
    statement: str
    files: dict[str, str]


class ReviewRevealedIssue(BaseModel):
    id: str
    file: str
    lines: tuple[int, int]
    critical: bool
    description: str
    found: bool
    score: int
    reason: str


class ReviewRevealed(BaseModel):
    """The hidden part of a task, shown only for a graded attempt; the judge's notes stay out."""

    issues: list[ReviewRevealedIssue]
    traps: list[ReviewTrap]
    expected_verdict: Literal["approve", "request_changes"]


class ReviewAttemptOut(BaseModel):
    id: UUID
    task_key: str
    status: str
    comments: list[ReviewCommentIn]
    verdict: str | None
    summary: str | None
    result: ReviewResult | None
    error: str | None = None  # why a `failed` attempt failed; judge-side text only
    revealed: ReviewRevealed | None
    submitted_at: datetime | None
    created_at: datetime


class ReviewReportIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    section: str | None = Field(None, max_length=200)
