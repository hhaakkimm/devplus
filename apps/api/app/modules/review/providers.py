from dishka import Provider, Scope, provide

from app.modules.review.service import ReviewService


class ReviewProvider(Provider):
    scope = Scope.REQUEST

    review_service = provide(ReviewService)
