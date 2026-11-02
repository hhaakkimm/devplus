from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.modules.auth.service import CurrentUser
from app.modules.code_review.schemas import AttemptOut, DraftIn, ReportIn, TaskListOut, TaskOut
from app.modules.code_review.service import CodeReviewService

router = APIRouter(prefix="/api/code-review", route_class=DishkaRoute)


@router.get("/tasks")
async def list_tasks(
    user: FromDishka[CurrentUser], service: FromDishka[CodeReviewService]
) -> list[TaskListOut]:
    return await service.list_tasks(user)


@router.get("/tasks/{module}/{slug}")
async def get_task(
    module: str, slug: str, user: FromDishka[CurrentUser], service: FromDishka[CodeReviewService]
) -> TaskOut:
    return await service.get_task(user, module, slug)


@router.post("/tasks/{module}/{slug}/attempts", status_code=201)
async def create_attempt(
    module: str, slug: str, user: FromDishka[CurrentUser], service: FromDishka[CodeReviewService]
) -> AttemptOut:
    return await service.create_attempt(user, module, slug)


@router.get("/attempts")
async def list_attempts(
    user: FromDishka[CurrentUser], service: FromDishka[CodeReviewService]
) -> list[AttemptOut]:
    return await service.list_attempts(user)


@router.put("/attempts/{attempt_id}")
async def save_draft(
    attempt_id: UUID,
    body: DraftIn,
    user: FromDishka[CurrentUser],
    service: FromDishka[CodeReviewService],
) -> AttemptOut:
    return await service.save_draft(user, attempt_id, body)


@router.get("/attempts/{attempt_id}")
async def get_attempt(
    attempt_id: UUID, user: FromDishka[CurrentUser], service: FromDishka[CodeReviewService]
) -> AttemptOut:
    return await service.get_attempt(user, attempt_id)


@router.post("/attempts/{attempt_id}/submit")
async def submit(
    attempt_id: UUID, user: FromDishka[CurrentUser], service: FromDishka[CodeReviewService]
) -> AttemptOut:
    return await service.submit(user, attempt_id)


@router.post("/attempts/{attempt_id}/report", status_code=204)
async def report(
    attempt_id: UUID,
    body: ReportIn,
    user: FromDishka[CurrentUser],
    service: FromDishka[CodeReviewService],
) -> None:
    await service.report(user, attempt_id, body)
