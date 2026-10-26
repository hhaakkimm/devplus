from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from app.modules.auth.service import CurrentUser
from app.modules.review.schemas import CheckIn, CheckOut, ReviewIn, ReviewOut
from app.modules.review.service import ReviewService

router = APIRouter(prefix="/api/review", route_class=DishkaRoute)


@router.post("", status_code=201)
async def create_review(
    body: ReviewIn, user: FromDishka[CurrentUser], reviews: FromDishka[ReviewService]
) -> ReviewOut:
    return await reviews.review(user, body)


@router.get("/{review_id}")
async def get_review(
    review_id: UUID, user: FromDishka[CurrentUser], reviews: FromDishka[ReviewService]
) -> ReviewOut:
    return await reviews.get(user, review_id)


@router.post("/{review_id}/check", status_code=201)
async def check_review(
    review_id: UUID,
    body: CheckIn,
    user: FromDishka[CurrentUser],
    reviews: FromDishka[ReviewService],
) -> CheckOut:
    return await reviews.check(user, review_id, body)
