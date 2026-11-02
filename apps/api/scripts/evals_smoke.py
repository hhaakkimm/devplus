"""Live check: one real Haiku call. Needs ANTHROPIC_API_KEY or EVALS_LLM_BACKEND=claude_cli;
not in CI."""

import asyncio
import sys
from pathlib import Path

# Run as a plain script: the project is not installed, so make `app` importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main() -> None:
    from app.modules.evals.llm import CompletionRequest
    from scripts.live_llm import live_llm

    async with live_llm() as llm:
        c = await llm.complete(
            CompletionRequest(
                "claude-haiku-5-5", "Answer in one word.", "Say hello.", "low", max_tokens=1024
            )
        )
    print(f"text: {c.text!r}")
    print(f"stop_reason: {c.stop_reason}")  # max_tokens here means thinking ate the whole limit
    print(f"tokens: in={c.input_tokens} out={c.output_tokens} latency={c.latency_ms}ms")
    print(f"cost: ${c.cost_usd:.6f}")


asyncio.run(main())
