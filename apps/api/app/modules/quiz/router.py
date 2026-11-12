from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Path

from app.core.errors import BadRequest
from app.modules.auth.service import CurrentUser
from app.modules.quiz.schemas import QuizResultIn, QuizResultsOut
from app.modules.quiz.service import QuizService

router = APIRouter(prefix="/api", route_class=DishkaRoute)

SlugPart = Annotated[str, Path(pattern=r"^[a-z0-9-]+$")]


# shortcut: a renamed quiz orphans its results; add a manifest if renames become common
def quiz_slug(module: str, quiz: str) -> str:
    slug = f"{module}/{quiz}"
    if len(slug) > 200:
        raise BadRequest("Quiz slug too long")
    return slug


@router.get("/quizzes/results")
async def list_results(
    user: FromDishka[CurrentUser], quizzes: FromDishka[QuizService]
) -> QuizResultsOut:
    return QuizResultsOut(results=await quizzes.list_results(user.id))


# shortcut: the client reports its own score; add server-side checking if a leaderboard appears
@router.put("/quizzes/{module}/{quiz}/result", status_code=204)
async def record_result(
    module: SlugPart,
    quiz: SlugPart,
    body: QuizResultIn,
    user: FromDishka[CurrentUser],
    quizzes: FromDishka[QuizService],
) -> None:
    await quizzes.record(user.id, quiz_slug(module, quiz), body.score, body.total)
