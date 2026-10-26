"""Live check: one real Haiku call via AnthropicLLMClient. Needs ANTHROPIC_API_KEY; not in CI."""

import asyncio
import os
import sys
from pathlib import Path

# Run as a plain script: the project is not installed, so make `app` importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main() -> None:
    import anthropic

    from app.modules.evals.llm import AnthropicLLMClient, CompletionRequest

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set")
    async with anthropic.AsyncAnthropic(api_key=api_key) as client:
        c = await AnthropicLLMClient(client).complete(
            CompletionRequest(
                "claude-haiku-5-5", "Answer in one word.", "Say hello.", "low", max_tokens=1024
            )
        )
    print(f"text: {c.text!r}")
    print(f"stop_reason: {c.stop_reason}")  # max_tokens here means thinking ate the whole limit
    print(f"tokens: in={c.input_tokens} out={c.output_tokens} latency={c.latency_ms}ms")
    print(f"cost: ${c.cost_usd:.6f}")


asyncio.run(main())
