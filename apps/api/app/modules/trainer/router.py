from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.modules.auth.service import CurrentUser
from app.modules.evals.service import RunOut
from app.modules.trainer.schemas import AttemptIn, TaskOut
from app.modules.trainer.service import TrainerService

router = APIRouter(prefix="/api/trainer", route_class=DishkaRoute)


@router.get("/tasks")
async def list_tasks(
    user: FromDishka[CurrentUser], trainer: FromDishka[TrainerService]
) -> list[TaskOut]:
    return await trainer.list(user)


@router.post("/tasks/{module}/{task}/attempts", status_code=201)
async def submit_attempt(
    module: str,
    task: str,
    body: AttemptIn,
    user: FromDishka[CurrentUser],
    trainer: FromDishka[TrainerService],
) -> RunOut:
    return await trainer.submit(user, module, task, body)


@router.get("/tasks/{module}/{task}/attempts")
async def list_attempts(
    module: str, task: str, user: FromDishka[CurrentUser], trainer: FromDishka[TrainerService]
) -> list[RunOut]:
    return await trainer.attempts(user, module, task)
