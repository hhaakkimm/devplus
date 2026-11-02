import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from app.core.config import Settings
from app.core.container import build_container
from app.modules.evals.llm import ClaudeCliLLMClient, CompletionRequest, LLMClient, LLMError
from app.modules.review.critic import CriticFailed, critique

# A stand-in for the `claude` binary: records how it was called, then prints what the spec says.
FAKE_CLAUDE = """
import json, os, sys, time
spec = json.load(open(os.environ["FAKE_SPEC"]))
json.dump(
    {"argv": sys.argv[1:], "stdin": sys.stdin.read(),
     "api_key": os.environ.get("ANTHROPIC_API_KEY"),
     "max_out": os.environ.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS"), "pid": os.getpid()},
    open(spec["record"], "w"),
)
time.sleep(spec.get("sleep", 0))
sys.stdout.write(spec.get("stdout", ""))
sys.stderr.write(spec.get("stderr", ""))
sys.exit(spec.get("code", 0))
"""

OK_REPLY = {
    "is_error": False,
    "result": '{"w":"Hi"}',
    "structured_output": {"w": "Hi"},
    "stop_reason": "tool_use",
    "usage": {
        "input_tokens": 2,
        "output_tokens": 114,
        "cache_read_input_tokens": 5,
        "cache_creation_input_tokens": 1080,
    },
}


@pytest.fixture
def cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    script = tmp_path / "fake_claude.py"
    script.write_text(FAKE_CLAUDE)
    record = tmp_path / "record.json"

    def make(**spec: Any) -> ClaudeCliLLMClient:
        (tmp_path / "spec.json").write_text(json.dumps({"record": str(record), **spec}))
        monkeypatch.setenv("FAKE_SPEC", str(tmp_path / "spec.json"))
        return ClaudeCliLLMClient(command=(sys.executable, str(script)))

    make.record = lambda: json.loads(record.read_text())  # type: ignore[attr-defined]
    return make


async def test_call_shape(cli, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-must-not-reach-the-cli")
    client = cli(stdout=json.dumps(OK_REPLY))
    schema = {"type": "object"}
    await client.complete(
        CompletionRequest("claude-haiku-5-5", "SYS", "the user text", "low", 256, schema)
    )
    seen = cli.record()
    argv = seen["argv"]
    assert argv[:1] == ["-p"]
    assert argv[argv.index("--model") + 1] == "claude-haiku-5-5"
    assert argv[argv.index("--effort") + 1] == "low"
    assert argv[argv.index("--system-prompt") + 1] == "SYS"
    assert json.loads(argv[argv.index("--json-schema") + 1]) == schema
    assert argv[argv.index("--tools") + 1] == ""  # a plain model call: no file or shell access
    assert "--no-session-persistence" in argv
    assert seen["stdin"] == "the user text"  # not in argv: long, and visible in `ps`
    assert seen["api_key"] is None  # the point is the subscription login, not a key
    assert seen["max_out"] == "256"


async def test_no_schema_and_empty_system(cli):
    client = cli(stdout=json.dumps({**OK_REPLY, "structured_output": None, "result": "plain"}))
    got = await client.complete(CompletionRequest("claude-haiku-5-5", "", "hi"))
    argv = cli.record()["argv"]
    assert "--system-prompt" not in argv
    assert "--json-schema" not in argv
    assert got.text == "plain"
    assert got.json is None


async def test_completion_fields(cli):
    client = cli(stdout=json.dumps(OK_REPLY))
    got = await client.complete(
        CompletionRequest("claude-haiku-5-5", "S", "u", output_schema={"type": "object"})
    )
    assert got.json == {"w": "Hi"}
    assert got.text == '{"w":"Hi"}'
    assert got.model == "claude-haiku-5-5"
    # the CLI reports a structured answer as a tool use: that is a normal end
    assert got.stop_reason == "end_turn"
    assert (got.input_tokens, got.output_tokens) == (2, 114)
    assert (got.cache_read_tokens, got.cache_write_tokens) == (5, 1080)
    assert got.latency_ms >= 0


async def test_schema_answer_without_structured_output_is_parsed_from_text(cli):
    client = cli(stdout=json.dumps({**OK_REPLY, "structured_output": None}))
    got = await client.complete(
        CompletionRequest("claude-haiku-5-5", "S", "u", output_schema={"type": "object"})
    )
    assert got.json == {"w": "Hi"}


@pytest.mark.parametrize("raw", ["max_tokens", "refusal"])
async def test_stop_reasons_the_callers_act_on_are_kept(cli, raw):
    client = cli(stdout=json.dumps({**OK_REPLY, "stop_reason": raw}))
    got = await client.complete(CompletionRequest("claude-haiku-5-5", "S", "u"))
    assert got.stop_reason == raw


async def test_error_reply_raises(cli):
    reply = {"is_error": True, "result": "Not logged in · Please run /login"}
    client = cli(stdout=json.dumps(reply), code=1)
    with pytest.raises(LLMError, match="Not logged in"):
        await client.complete(CompletionRequest("claude-haiku-5-5", "S", "u"))


async def test_crash_without_json_raises_with_stderr(cli):
    client = cli(stdout="", stderr="boom", code=2)
    with pytest.raises(LLMError, match="boom"):
        await client.complete(CompletionRequest("claude-haiku-5-5", "S", "u"))


async def test_garbage_output_raises(cli):
    client = cli(stdout="not json")
    with pytest.raises(LLMError, match="JSON"):
        await client.complete(CompletionRequest("claude-haiku-5-5", "S", "u"))


async def test_missing_binary_raises():
    client = ClaudeCliLLMClient(command=("/nonexistent/claude",))
    with pytest.raises(LLMError, match="claude"):
        await client.complete(CompletionRequest("claude-haiku-5-5", "S", "u"))


async def test_cancel_kills_the_process(cli):
    client = cli(stdout=json.dumps(OK_REPLY), sleep=30)
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(1):
            await client.complete(CompletionRequest("claude-haiku-5-5", "S", "u"))
    pid = cli.record()["pid"]
    await asyncio.sleep(0.1)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)  # nothing is left running on the subscription


async def test_count_tokens_is_an_estimate(cli):
    client = cli()
    assert (
        await client.count_tokens(CompletionRequest("claude-haiku-5-5", "a" * 40, "b" * 40)) == 20
    )


async def test_provider_claude_cli_backend(settings: Settings):
    container = build_container(settings.model_copy(update={"evals_llm_backend": "claude_cli"}))
    try:
        assert isinstance(await container.get(LLMClient), ClaudeCliLLMClient)
    finally:
        await container.close()


async def test_a_failed_cli_call_is_a_failed_critic_not_a_crash():
    class Broken:
        async def complete(self, req: CompletionRequest):
            raise LLMError("Not logged in")

    with pytest.raises(CriticFailed):
        await critique(Broken(), "system", "template")  # type: ignore[arg-type]
