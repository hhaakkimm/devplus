"""Live check of the code review judge on the real task: its reference review must pass and a
careless one must not. Needs ANTHROPIC_API_KEY (spends money) or EVALS_LLM_BACKEND=claude_cli
(spends the subscription); not in CI."""

import asyncio
import sys
from pathlib import Path

# Run as a plain script: the project is not installed, so make `app` importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CONTENT_DIR = Path(__file__).resolve().parents[3] / "content"


async def main() -> int:
    from app.modules.code_review.judge import grade_review
    from app.modules.code_review.tasks import ReviewComment, load_tasks
    from scripts.live_llm import live_llm

    task = load_tasks(CONTENT_DIR)[0]  # the first real task
    trap = task.traps[0]
    # no issue found and a wrong verdict: a comment on correct code
    careless = [
        ReviewComment(
            file=trap.file,
            line_start=trap.lines[0],
            line_end=trap.lines[1],
            text="Тут что-то не так, лучше переписать.",
        )
    ]
    runs = [
        ("reference", task.reference, task.reference_verdict, True),
        ("careless", careless, "approve", False),
    ]
    ok = True
    async with live_llm() as llm:
        print(f"task: {task.key}")
        for name, comments, verdict, should_pass in runs:
            result, cost, error = await grade_review(llm, task, comments, verdict, None)
            print(f"\n[{name}] cost: ${cost:.6f}")
            if result is None:
                print(f"judge failed: {error}")
                ok = False
                continue
            for i in result.issues:
                print(f"  {i.id}: found={i.found} score={i.score} {i.reason}")
            for g in result.general:
                print(f"  {g.name}: score={g.score} {g.reason}")
            print(f"  score={result.score:.2f} passed={result.passed}")
            if result.passed != should_pass:
                print(f"  UNEXPECTED: {name} review should {'' if should_pass else 'not '}pass")
                ok = False
    return 0 if ok else 1


sys.exit(asyncio.run(main()))
