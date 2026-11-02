from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import Conflict, NotFound, Unprocessable
from app.modules.auth.service import CurrentUser
from app.modules.code_review.judge import ReviewResult, file_lines
from app.modules.code_review.models import ReviewAttempt
from app.modules.code_review.schemas import (
    AttemptOut,
    CommentIn,
    DraftIn,
    Revealed,
    RevealedIssue,
    TaskListOut,
    TaskOut,
)
from app.modules.code_review.tasks import TaskSpec, cached_tasks
from app.modules.evals.service import LLMClient


def _task_out(task: TaskSpec) -> TaskOut:
    # an explicit whitelist: a field added to TaskSpec stays hidden until it is listed here
    return TaskOut(
        module=task.module,
        slug=task.slug,
        title=task.title,
        difficulty=task.difficulty,
        estimate_min=task.estimate_min,
        statement=task.statement,
        files=task.files,
    )


def _revealed(task: TaskSpec, result: ReviewResult) -> Revealed:
    found = {r.id: r for r in result.issues}
    return Revealed(
        issues=[
            RevealedIssue(
                id=i.id,
                file=i.file,
                lines=i.lines,
                critical=i.critical,
                description=i.description,
                found=found[i.id].found,
                score=found[i.id].score,
                reason=found[i.id].reason,
            )
            for i in task.issues
        ],
        traps=list(task.traps),
        expected_verdict=task.expected_verdict,
    )


class CodeReviewService:
    def __init__(self, session: AsyncSession, settings: Settings, llm: LLMClient) -> None:
        self.session = session
        self.settings = settings
        self.llm = llm  # for the judge, when an attempt is sent

    async def list_tasks(self, user: CurrentUser) -> list[TaskListOut]:
        rows = await self.session.execute(
            select(ReviewAttempt.task_key, ReviewAttempt.status, ReviewAttempt.result).where(
                ReviewAttempt.user_id == user.id
            )
        )
        attempted: set[str] = set()
        passed: set[str] = set()
        for key, status, result in rows:
            attempted.add(key)
            if status == "graded" and result is not None and result["passed"]:
                passed.add(key)
        return [
            TaskListOut(
                module=t.module,
                slug=t.slug,
                title=t.title,
                difficulty=t.difficulty,
                estimate_min=t.estimate_min,
                status="passed"
                if t.key in passed
                else "attempted"
                if t.key in attempted
                else "not_started",
            )
            for t in self._tasks()
        ]

    async def get_task(self, user: CurrentUser, module: str, slug: str) -> TaskOut:
        return _task_out(self._task(module, slug))

    async def create_attempt(self, user: CurrentUser, module: str, slug: str) -> AttemptOut:
        key = self._task(module, slug).key
        # shortcut: two simultaneous first requests may both create a draft, add a partial unique
        # index (user_id, task_key) where status = 'draft' if that ever shows up
        draft = await self.session.scalar(
            select(ReviewAttempt).where(
                ReviewAttempt.user_id == user.id,
                ReviewAttempt.task_key == key,
                ReviewAttempt.status == "draft",
            )
        )
        if draft is None:
            draft = ReviewAttempt(user_id=user.id, task_key=key, status="draft")
            self.session.add(draft)
            await self.session.commit()
            await self.session.refresh(draft)
        return self._out(draft)

    async def save_draft(self, user: CurrentUser, attempt_id: UUID, body: DraftIn) -> AttemptOut:
        attempt = await self._own(user, attempt_id)
        if attempt.status != "draft":
            raise Conflict("Попытка уже отправлена, править её нельзя")
        self._check_comments(self._task_of(attempt), body.comments)
        attempt.comments = [c.model_dump() for c in body.comments]
        attempt.verdict = body.verdict
        attempt.summary = body.summary
        await self.session.commit()
        return self._out(attempt)

    async def get_attempt(self, user: CurrentUser, attempt_id: UUID) -> AttemptOut:
        return self._out(await self._own(user, attempt_id))

    async def list_attempts(self, user: CurrentUser) -> list[AttemptOut]:
        rows = await self.session.scalars(
            select(ReviewAttempt)
            .where(ReviewAttempt.user_id == user.id)
            .order_by(ReviewAttempt.created_at.desc(), ReviewAttempt.id)
        )
        return [self._out(a) for a in rows]

    def _tasks(self) -> tuple[TaskSpec, ...]:
        return cached_tasks(Path(self.settings.content_dir))

    def _task(self, module: str, slug: str) -> TaskSpec:
        # matched against the loaded list only: the URL never becomes a path
        for task in self._tasks():
            if (task.module, task.slug) == (module, slug):
                return task
        raise NotFound("Не найдено")

    def _task_of(self, attempt: ReviewAttempt) -> TaskSpec:
        module, _, slug = attempt.task_key.partition("/")
        return self._task(module, slug)

    async def _own(self, user: CurrentUser, attempt_id: UUID) -> ReviewAttempt:
        attempt = await self.session.get(ReviewAttempt, attempt_id)
        if attempt is None or attempt.user_id != user.id:  # someone else's: not "forbidden"
            raise NotFound("Не найдено")
        return attempt

    @staticmethod
    def _check_comments(task: TaskSpec, comments: list[CommentIn]) -> None:
        for n, c in enumerate(comments, 1):
            if c.file not in task.files:
                raise Unprocessable(f"Замечание {n}: в задаче нет файла {c.file}")
            if c.line_start > c.line_end:
                raise Unprocessable(f"Замечание {n}: начало диапазона позже конца")
            if c.line_end > len(file_lines(task.files[c.file])):
                raise Unprocessable(f"Замечание {n}: в файле {c.file} нет строки {c.line_end}")

    def _out(self, attempt: ReviewAttempt) -> AttemptOut:
        result = ReviewResult.model_validate(attempt.result) if attempt.result else None
        revealed = None
        if attempt.status == "graded" and result is not None:
            revealed = _revealed(self._task_of(attempt), result)
        return AttemptOut(
            id=attempt.id,
            task_key=attempt.task_key,
            status=attempt.status,
            comments=[CommentIn.model_validate(c) for c in attempt.comments],
            verdict=attempt.verdict,
            summary=attempt.summary,
            result=result if attempt.status == "graded" else None,
            revealed=revealed,
            submitted_at=attempt.submitted_at,
            created_at=attempt.created_at,
        )
