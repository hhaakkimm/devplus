from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.modules.auth.service import CurrentUser
from app.modules.evals.schemas import (
    PromptDetailOut,
    PromptIn,
    PromptPatch,
    PromptSummaryOut,
    VersionIn,
    VersionOut,
)
from app.modules.evals.service import PromptService

router = APIRouter(prefix="/api/evals", route_class=DishkaRoute)


@router.post("/prompts", status_code=201)
async def create_prompt(
    body: PromptIn, user: FromDishka[CurrentUser], prompts: FromDishka[PromptService]
) -> PromptDetailOut:
    return await prompts.create(user, body.name, body.version)


@router.get("/prompts")
async def list_prompts(
    user: FromDishka[CurrentUser], prompts: FromDishka[PromptService]
) -> list[PromptSummaryOut]:
    return await prompts.list(user)


@router.get("/prompts/{prompt_id}")
async def get_prompt(
    prompt_id: UUID, user: FromDishka[CurrentUser], prompts: FromDishka[PromptService]
) -> PromptDetailOut:
    return await prompts.get(user, prompt_id)


@router.patch("/prompts/{prompt_id}")
async def update_prompt(
    prompt_id: UUID,
    body: PromptPatch,
    user: FromDishka[CurrentUser],
    prompts: FromDishka[PromptService],
) -> PromptSummaryOut:
    return await prompts.update(user, prompt_id, body.name, body.shared)


@router.post("/prompts/{prompt_id}/versions", status_code=201)
async def add_version(
    prompt_id: UUID,
    body: VersionIn,
    user: FromDishka[CurrentUser],
    prompts: FromDishka[PromptService],
) -> VersionOut:
    return await prompts.add_version(user, prompt_id, body)


@router.post("/prompts/{prompt_id}/copy", status_code=201)
async def copy_prompt(
    prompt_id: UUID, user: FromDishka[CurrentUser], prompts: FromDishka[PromptService]
) -> PromptDetailOut:
    return await prompts.copy(user, prompt_id)
