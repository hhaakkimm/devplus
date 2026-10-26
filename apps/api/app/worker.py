"""Taskiq worker: `taskiq worker app.worker:broker`.

Runs `execute_run` for the runs the API queues. The API sends it by name through its own broker
(`TaskiqRunQueue`) and never imports this module.
"""

import logging
from uuid import UUID

from dishka import AsyncContainer
from dishka.integrations.taskiq import FromDishka, TaskiqProvider, inject, setup_dishka
from taskiq import AsyncBroker, TaskiqEvents, TaskiqState

from app.core.config import Settings
from app.core.container import build_container
from app.core.logging import configure_logging
from app.modules.evals.executor import RunExecutor
from app.modules.evals.queue import TASK_NAME, make_broker

logger = logging.getLogger(__name__)


def setup_worker(broker: AsyncBroker, container: AsyncContainer) -> None:
    """Puts `execute_run` and the start-up recovery on `broker`; tests call it with their own."""
    setup_dishka(container, broker)

    # task_name: taskiq would name it `app.worker:execute_run`, and the API sends `execute_run`
    @broker.task(task_name=TASK_NAME)
    @inject(patch_module=True)
    async def execute_run(run_id: str, executor: FromDishka[RunExecutor]) -> None:
        await executor.execute(UUID(run_id))

    @broker.on_event(TaskiqEvents.WORKER_STARTUP)
    async def recover(_: TaskiqState) -> None:
        async with container() as request:
            failed, queued = await (await request.get(RunExecutor)).recover()
        logger.info("worker started: %d interrupted runs failed, %d requeued", failed, len(queued))
        for run_id in queued:
            # `inject` drops `executor` from the call, not from the type
            await execute_run.kiq(str(run_id))  # type: ignore[call-overload]

    @broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
    async def close(_: TaskiqState) -> None:
        await container.close()


settings = Settings()
broker = make_broker(settings)
# first handler: the start-up recovery below logs through it
broker.on_event(TaskiqEvents.WORKER_STARTUP)(lambda _: configure_logging())
setup_worker(broker, build_container(settings, TaskiqProvider()))
