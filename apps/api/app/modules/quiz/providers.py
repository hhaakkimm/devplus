from dishka import Provider, Scope, provide

from app.modules.quiz.service import QuizService


class QuizProvider(Provider):
    scope = Scope.REQUEST

    quiz_service = provide(QuizService)
