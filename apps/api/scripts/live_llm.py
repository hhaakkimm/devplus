"""The live LLM client of the smoke scripts: the Claude Code login (EVALS_LLM_BACKEND=claude_cli)
or the API (ANTHROPIC_API_KEY). Not in CI."""

import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.modules.evals.llm import AnthropicLLMClient, ClaudeCliLLMClient, LLMClient


@asynccontextmanager
async def live_llm() -> AsyncIterator[LLMClient]:
    if os.environ.get("EVALS_LLM_BACKEND") == "claude_cli":
        yield ClaudeCliLLMClient()
        return
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set (or use EVALS_LLM_BACKEND=claude_cli)")
    async with anthropic.AsyncAnthropic(api_key=api_key) as client:
        yield AnthropicLLMClient(client)
