from dishka import Provider, Scope, provide

from app.modules.simulator.service import SimulatorService


class SimulatorProvider(Provider):
    scope = Scope.REQUEST

    simulator_service = provide(SimulatorService)
