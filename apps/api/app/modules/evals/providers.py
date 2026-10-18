from collections.abc import AsyncIterator

import anthropic
from dishka import Provider, Scope, provide

from app.core.config import Settings
from app.modules.evals.llm import AnthropicLLMClient, FakeLLMClient, LLMClient


class EvalsProvider(Provider):
    @provide(scope=Scope.APP)
    async def llm(self, settings: Settings) -> AsyncIterator[LLMClient]:
        if settings.evals_llm_backend == "fake":
            yield FakeLLMClient()
            return
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        try:
            yield AnthropicLLMClient(client)
        finally:
            await client.close()
