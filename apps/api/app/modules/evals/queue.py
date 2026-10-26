import asyncio
from typing import Any, Protocol
from uuid import UUID

from taskiq import AsyncBroker
from taskiq.kicker import AsyncKicker
from taskiq_redis import ListQueueBroker

from app.core.config import Settings

TASK_NAME = "execute_run"


class RunQueue(Protocol):
    async def enqueue(self, run_id: UUID) -> None: ...


def make_broker(settings: Settings) -> ListQueueBroker:
    # redis-py 8 reads with a 5 s timeout by default, and the worker's BRPOP blocks until a task
    # arrives: an idle worker would crash every 5 s and fail the runs it was executing.
    # shortcut: the API's enqueue has no read timeout either, so a hung Redis hangs the request;
    # split a producer broker out if that ever happens
    return ListQueueBroker(settings.redis_url, socket_timeout=None, socket_connect_timeout=5)


class TaskiqRunQueue:
    """Sends `execute_run` by name: the API never imports the task, only the worker defines it."""

    def __init__(self, broker: AsyncBroker) -> None:
        self.broker = broker
        self._started = False
        self._start_lock = asyncio.Lock()

    async def enqueue(self, run_id: UUID) -> None:
        async with self._start_lock:  # two first sends must not both start the broker
            if not self._started:  # lazily, so an API without Redis still boots
                await self.broker.startup()
                self._started = True
        # `...`: the kicker cannot know the signature of a task it does not import
        await AsyncKicker[..., Any](TASK_NAME, self.broker, {}).kiq(run_id=str(run_id))

    async def close(self) -> None:
        await self.broker.shutdown()
