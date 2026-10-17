from dishka import Provider, Scope, provide

from app.modules.progress.service import ProgressService


class ProgressProvider(Provider):
    scope = Scope.REQUEST

    progress_service = provide(ProgressService)
