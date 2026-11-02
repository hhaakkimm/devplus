import asyncio
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, null, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import Conflict, DomainError, NotFound, Unprocessable
from app.modules.auth.service import CurrentUser
from app.modules.code_review.judge import ReviewResult, file_lines, grade_review
from app.modules.code_review.models import ReviewAttempt, ReviewFeedbackReport
from app.modules.code_review.schemas import (
    AttemptOut,
    CommentIn,
    DraftIn,
    ReportIn,
    Revealed,
    RevealedIssue,
    TaskListOut,
    TaskOut,
)
from app.modules.code_review.tasks import ReviewComment, TaskSpec, cached_tasks
from app.modules.evals.service import LLMClient

logger = logging.getLogger(__name__)

SENT = "Попытка уже отправлена, править её нельзя"
GRADING_TIMEOUT = timedelta(minutes=10)  # a longer `grading` means the request died: failed
JUDGE_TIMEOUT = GRADING_TIMEOUT - timedelta(minutes=1)  # a live call ends before it looks dead
DAY = timedelta(hours=24)


class JudgeUnavailable(DomainError):
    status_code = 502


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
        draft = await self._draft(user, key)
        if draft is None:
            draft = ReviewAttempt(user_id=user.id, task_key=key, status="draft")
            try:
                async with self.session.begin_nested():
                    self.session.add(draft)
            except IntegrityError:  # a simultaneous request created the draft first
                draft = await self._draft(user, key)
                if draft is None:  # deleted in between: not worth another round
                    raise
            await self.session.commit()
            await self.session.refresh(draft)
        return self._out(draft)

    async def _draft(self, user: CurrentUser, key: str) -> ReviewAttempt | None:
        return await self.session.scalar(
            select(ReviewAttempt)
            .where(
                ReviewAttempt.user_id == user.id,
                ReviewAttempt.task_key == key,
                ReviewAttempt.status == "draft",
            )
            .order_by(ReviewAttempt.created_at, ReviewAttempt.id)
            .limit(1)
        )

    async def save_draft(self, user: CurrentUser, attempt_id: UUID, body: DraftIn) -> AttemptOut:
        attempt = await self._own(user, attempt_id)
        if attempt.status != "draft":
            raise Conflict(SENT)
        self._check_comments(self._task_of(attempt), body.comments)
        # conditional, so a submit that has just taken the draft never has its comments replaced
        saved = await self.session.scalar(
            update(ReviewAttempt)
            .where(ReviewAttempt.id == attempt.id, ReviewAttempt.status == "draft")
            .values(
                comments=[c.model_dump() for c in body.comments],
                verdict=body.verdict,
                summary=body.summary,
            )
            .returning(ReviewAttempt.id)
            .execution_options(synchronize_session=False)
        )
        if saved is None:
            raise Conflict(SENT)
        await self.session.commit()
        await self.session.refresh(attempt)
        return self._out(attempt)

    async def submit(self, user: CurrentUser, attempt_id: UUID) -> AttemptOut:
        # one claim per user at a time: the limit is counted after the previous claim committed
        await self.session.execute(
            select(func.pg_advisory_xact_lock(func.hashtext(f"code_review:{user.id}")))
        )
        attempt = await self._own(user, attempt_id, lock=True)
        if self._status(attempt) not in ("draft", "failed"):
            raise Conflict("Попытка уже отправлена")
        task = self._task_of(attempt)
        comments = [CommentIn.model_validate(c) for c in attempt.comments]
        verdict, summary = attempt.verdict, attempt.summary
        if verdict is None:
            raise Unprocessable("Выберите вердикт: approve или request_changes")
        if not comments and not (summary or "").strip():
            raise Unprocessable("Добавьте хотя бы одно замечание или резюме")
        self._check_comments(task, comments)  # the task file may have changed since the draft
        now = datetime.now(UTC)
        sent = await self.session.scalar(
            select(func.count())
            .select_from(ReviewAttempt)
            .where(
                ReviewAttempt.user_id == user.id,
                ReviewAttempt.submitted_at >= now - DAY,
                or_(
                    ReviewAttempt.status == "graded",
                    and_(
                        ReviewAttempt.status == "grading",
                        ReviewAttempt.submitted_at >= now - GRADING_TIMEOUT,
                    ),
                ),
            )
        )
        if (sent or 0) >= self.settings.code_review_daily_limit:
            raise Conflict(
                f"Суточный лимит разборов исчерпан ({self.settings.code_review_daily_limit}), "
                "попробуйте завтра"
            )
        # the only way into `grading`: of two simultaneous sends one matches no row and gets a 409
        claimed = await self.session.scalar(
            update(ReviewAttempt)
            .where(
                ReviewAttempt.id == attempt.id,
                ReviewAttempt.user_id == user.id,
                or_(
                    ReviewAttempt.status.in_(("draft", "failed")),
                    and_(
                        ReviewAttempt.status == "grading",
                        ReviewAttempt.submitted_at < now - GRADING_TIMEOUT,
                    ),
                ),
            )
            .values(status="grading", submitted_at=now, result=null(), cost_usd=None)
            .returning(ReviewAttempt.id)
            .execution_options(synchronize_session=False)
        )
        if claimed is None:
            raise Conflict("Попытка уже отправлена")
        await self.session.commit()  # before the judge: no transaction is held during its call
        try:
            async with asyncio.timeout(JUDGE_TIMEOUT.total_seconds()):
                result, cost, error = await grade_review(
                    self.llm,
                    task,
                    [ReviewComment.model_validate(c.model_dump()) for c in comments],
                    verdict,
                    summary,
                )
        except Exception as e:  # network, SDK: the attempt must not stay in `grading`
            logger.warning("judge call failed: %s", e, exc_info=True)
            await self._finish(attempt, now, "failed", {"error": "Судья недоступен"}, None)
            raise JudgeUnavailable("Судья сейчас недоступен, попробуйте отправить ещё раз") from e
        if result is None:
            await self._finish(attempt, now, "failed", {"error": error}, cost)
        else:
            await self._finish(attempt, now, "graded", result.model_dump(mode="json"), cost)
        return self._out(attempt)

    async def _finish(
        self,
        attempt: ReviewAttempt,
        sent_at: datetime,
        status: str,
        result: dict[str, Any],
        cost: Decimal | None,
    ) -> None:
        # shortcut: if a stale attempt was sent again meanwhile, this late answer and its cost
        # are dropped; keep the cost somewhere if that ever becomes visible
        done = await self.session.scalar(
            update(ReviewAttempt)
            .where(
                ReviewAttempt.id == attempt.id,
                ReviewAttempt.status == "grading",
                ReviewAttempt.submitted_at == sent_at,
            )
            .values(status=status, result=result, cost_usd=cost)
            .returning(ReviewAttempt.id)
            .execution_options(synchronize_session=False)
        )
        await self.session.commit()
        if done is None:
            raise Conflict("Попытка отправлена повторно, этот разбор отброшен")
        await self.session.refresh(attempt)

    async def report(self, user: CurrentUser, attempt_id: UUID, body: ReportIn) -> None:
        attempt = await self._own(user, attempt_id)
        if attempt.status != "graded":
            raise Conflict("Пожаловаться можно на готовый разбор")
        self.session.add(
            ReviewFeedbackReport(
                attempt_id=attempt.id, user_id=user.id, section=body.section, text=body.text
            )
        )
        await self.session.commit()

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

    async def _own(
        self, user: CurrentUser, attempt_id: UUID, *, lock: bool = False
    ) -> ReviewAttempt:
        attempt = await self.session.get(
            ReviewAttempt,
            attempt_id,
            with_for_update=True if lock else None,
            populate_existing=lock,
        )
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

    @staticmethod
    def _status(attempt: ReviewAttempt) -> str:
        """`grading` for longer than the timeout is a request that died: shown as `failed`."""
        stale = attempt.submitted_at is not None and (
            attempt.submitted_at < datetime.now(UTC) - GRADING_TIMEOUT
        )
        return "failed" if attempt.status == "grading" and stale else attempt.status

    def _out(self, attempt: ReviewAttempt) -> AttemptOut:
        status = self._status(attempt)
        graded = status == "graded" and attempt.result is not None
        result = ReviewResult.model_validate(attempt.result) if graded else None
        revealed = None
        if result is not None:
            try:
                revealed = _revealed(self._task_of(attempt), result)
            except (NotFound, KeyError):  # the task was renamed or changed after the grading
                revealed = None
        error = attempt.result.get("error") if status == "failed" and attempt.result else None
        return AttemptOut(
            id=attempt.id,
            task_key=attempt.task_key,
            status=status,
            comments=[CommentIn.model_validate(c) for c in attempt.comments],
            verdict=attempt.verdict,
            summary=attempt.summary,
            result=result,
            error=error,
            revealed=revealed,
            submitted_at=attempt.submitted_at,
            created_at=attempt.created_at,
        )
