from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.modules.auth.service import CurrentUser
from app.modules.simulator.schemas import (
    SimAttemptIn,
    SimAttemptOut,
    SimComponentOut,
    SimRunIn,
    SimRunOut,
    SimTaskOut,
    SimTaskSummaryOut,
)
from app.modules.simulator.service import SimulatorService

router = APIRouter(prefix="/api/simulator", route_class=DishkaRoute)


@router.get("/components")
async def components(
    user: FromDishka[CurrentUser], simulator: FromDishka[SimulatorService]
) -> list[SimComponentOut]:
    return simulator.components()


@router.get("/tasks")
async def list_tasks(
    user: FromDishka[CurrentUser], simulator: FromDishka[SimulatorService]
) -> list[SimTaskSummaryOut]:
    return await simulator.tasks(user)


@router.get("/tasks/{module}/{task}")
async def get_task(
    module: str, task: str, user: FromDishka[CurrentUser], simulator: FromDishka[SimulatorService]
) -> SimTaskOut:
    return simulator.task(module, task)


@router.post("/tasks/{module}/{task}/run")
async def run(
    module: str,
    task: str,
    body: SimRunIn,
    user: FromDishka[CurrentUser],
    simulator: FromDishka[SimulatorService],
) -> SimRunOut:
    return simulator.run(module, task, body)


@router.post("/tasks/{module}/{task}/attempts", status_code=201)
async def submit(
    module: str,
    task: str,
    body: SimAttemptIn,
    user: FromDishka[CurrentUser],
    simulator: FromDishka[SimulatorService],
) -> SimAttemptOut:
    return await simulator.submit(user, module, task, body)


@router.get("/tasks/{module}/{task}/attempts")
async def list_attempts(
    module: str, task: str, user: FromDishka[CurrentUser], simulator: FromDishka[SimulatorService]
) -> list[SimAttemptOut]:
    return await simulator.attempts(user, module, task)
