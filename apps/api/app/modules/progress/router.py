from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Path

from app.core.errors import BadRequest
from app.modules.auth.service import CurrentUser
from app.modules.progress.schemas import ProgressOut
from app.modules.progress.service import ProgressService

router = APIRouter(prefix="/api", route_class=DishkaRoute)

SlugPart = Annotated[str, Path(pattern=r"^[a-z0-9-]+$")]


# shortcut: renaming a lesson orphans its progress; add a lesson manifest if renames become common
def lesson_slug(module: str, lesson: str) -> str:
    slug = f"{module}/{lesson}"
    if len(slug) > 200:
        raise BadRequest("Lesson slug too long")
    return slug


@router.get("/progress")
async def list_progress(
    user: FromDishka[CurrentUser], progress: FromDishka[ProgressService]
) -> ProgressOut:
    return ProgressOut(completed=await progress.list_completed(user.id))


@router.put("/progress/{module}/{lesson}", status_code=204)
async def mark_done(
    module: SlugPart,
    lesson: SlugPart,
    user: FromDishka[CurrentUser],
    progress: FromDishka[ProgressService],
) -> None:
    await progress.mark_done(user.id, lesson_slug(module, lesson))


@router.delete("/progress/{module}/{lesson}", status_code=204)
async def unmark(
    module: SlugPart,
    lesson: SlugPart,
    user: FromDishka[CurrentUser],
    progress: FromDishka[ProgressService],
) -> None:
    await progress.unmark(user.id, lesson_slug(module, lesson))
