from dishka import Provider, Scope, provide

from app.modules.trainer.service import TrainerService


class TrainerProvider(Provider):
    scope = Scope.REQUEST

    trainer_service = provide(TrainerService)
