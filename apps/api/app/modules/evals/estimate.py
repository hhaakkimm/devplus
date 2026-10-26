import math
from collections.abc import Sequence
from decimal import Decimal

from app.modules.evals import pricing
from app.modules.evals.graders import GraderConfig, LlmJudgeGrader
from app.modules.evals.llm import CompletionRequest, LLMClient
from app.modules.evals.schemas import CaseIn, VersionOut
from app.modules.evals.template import render

NO_REFERENCE_TOKENS = 300
JUDGE_OVERHEAD_TOKENS = 500  # the judge's own system prompt and message framing
JUDGE_OUTPUT_TOKENS = 400


async def estimate_run_cost(
    llm: LLMClient, version: VersionOut, cases: list[CaseIn], graders: Sequence[GraderConfig]
) -> Decimal:
    """Expected cost in USD, from one count_tokens call on the first case.

    Ignores prompt caching and thinking tokens (not knowable beforehand): the run-time limit
    check catches an overrun. The variables of every case must be present, `render` raises else.
    """
    prompts = [render(version.user_template, c.variables) for c in cases]
    system_chars = len(version.system)
    counted = await llm.count_tokens(CompletionRequest(version.model, version.system, prompts[0]))
    # tokens per character, measured once and applied to every text; max() keeps empty input safe
    ratio = Decimal(counted) / max(system_chars + len(prompts[0]), 1)

    def tokens(chars: int) -> int:
        return math.ceil(ratio * chars)

    judges = [g for g in graders if isinstance(g, LlmJudgeGrader)]
    total = Decimal(0)
    for case, prompt in zip(cases, prompts, strict=True):
        # the answer is as long as the reference, else a guess; max_tokens bounds it either way
        answer = tokens(len(case.expected)) if case.expected is not None else NO_REFERENCE_TOKENS
        answer = min(answer, version.max_tokens)
        total += pricing.cost_usd(version.model, tokens(system_chars + len(prompt)), answer)
        for judge in judges:
            rubric_chars = sum(len(s.name) + len(s.description) for s in judge.rubric)
            judge_in = JUDGE_OVERHEAD_TOKENS + tokens(len(prompt) + rubric_chars) + answer
            total += pricing.cost_usd(judge.model, judge_in, JUDGE_OUTPUT_TOKENS)
    return total
