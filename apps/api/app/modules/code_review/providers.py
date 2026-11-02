from dishka import Provider, Scope, provide

from app.modules.code_review.service import CodeReviewService


class CodeReviewProvider(Provider):
    scope = Scope.REQUEST

    code_review_service = provide(CodeReviewService)
