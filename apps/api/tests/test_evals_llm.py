import json
from decimal import Decimal
from typing import Any

import anthropic
import httpx2
import pytest

from app.core.config import Settings
from app.core.container import build_container
from app.modules.evals.llm import (
    AnthropicLLMClient,
    CompletionRequest,
    FakeLLMClient,
    LLMClient,
)
from app.modules.evals.pricing import cost_usd

FALLBACK_BETA = "server-side-fallback-2026-07-01"


def test_cost_usd_opus():
    assert cost_usd("claude-opus-5-5", 1_000_000, 1_000_000) == Decimal("24.00")
    assert cost_usd("claude-sonnet-5-5", 0, 0, cache_read_tokens=1_000_000) == Decimal("0.20")
    assert cost_usd("claude-opus-5-5", 0, 0, cache_write_tokens=1_000_000) == Decimal("5.00")


def test_cost_usd_haiku():
    assert cost_usd("claude-haiku-5-5", 1_000_000, 1_000_000) == Decimal("0.60")
    assert cost_usd("claude-haiku-5-5", 0, 0, cache_read_tokens=1_000_000) == Decimal("0.01")
    assert cost_usd("claude-haiku-5-5", 0, 0, cache_write_tokens=1_000_000) == Decimal("0.125")


def text_reply(
    *texts: str,
    model: str = "claude-opus-5-5",
    stop_reason: str = "end_turn",
    stop_details: dict[str, Any] | None = None,
    thinking: bool = False,
    usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    if thinking:
        content.append({"type": "thinking", "thinking": "hmm", "signature": "sig"})
    content += [{"type": "text", "text": t} for t in texts]
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_details": stop_details,
        "stop_sequence": None,
        "usage": usage or {"input_tokens": 1, "output_tokens": 1},
    }


@pytest.fixture
def captured() -> list[httpx2.Request]:
    return []


@pytest.fixture
def make_client(captured: list[httpx2.Request]):
    def make(reply: dict[str, Any]) -> AnthropicLLMClient:
        def handler(request: httpx2.Request) -> httpx2.Response:
            captured.append(request)
            return httpx2.Response(200, json=reply)

        http = anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler))
        return AnthropicLLMClient(anthropic.AsyncAnthropic(api_key="test", http_client=http))

    return make


def body(captured: list[httpx2.Request]) -> dict[str, Any]:
    return json.loads(captured[-1].content)  # type: ignore[no-any-return]


async def test_anthropic_request_shape(captured, make_client):
    client = make_client(text_reply("ok"))
    await client.complete(
        CompletionRequest("claude-opus-5-5", "SYS", "hi", "low", 256, {"type": "object"})
    )
    sent = body(captured)
    assert sent["model"] == "claude-opus-5-5"
    assert sent["max_tokens"] == 256
    assert sent["messages"] == [{"role": "user", "content": "hi"}]
    assert sent["system"] == [
        {"type": "text", "text": "SYS", "cache_control": {"type": "ephemeral"}}
    ]
    assert sent["thinking"] == {"type": "adaptive"}
    assert sent["output_config"] == {
        "effort": "low",
        "format": {"type": "json_schema", "schema": {"type": "object"}},
    }
    assert "fallbacks" not in sent
    assert captured[-1].url.path == "/v1/messages"


async def test_no_schema_and_empty_system(captured, make_client):
    client = make_client(text_reply("ok"))
    await client.complete(CompletionRequest("claude-haiku-5-5", "", "hi"))
    sent = body(captured)
    assert sent["output_config"] == {"effort": "medium"}
    assert "system" not in sent  # the API rejects an empty text block


@pytest.mark.parametrize(
    ("model", "allow_fallback", "expected"),
    [
        ("claude-sonnet-5-5", True, True),
        ("claude-opus-5-5", True, True),
        ("claude-sonnet-5-5", False, False),
        ("claude-haiku-5-5", True, False),
    ],
)
async def test_fallback_only_when_allowed_and_not_haiku(
    captured, make_client, model, allow_fallback, expected
):
    client = make_client(text_reply("ok", model=model))
    await client.complete(CompletionRequest(model, "SYS", "hi", allow_fallback=allow_fallback))
    sent, request = body(captured), captured[-1]
    if expected:
        assert sent["fallbacks"] == "default"
        assert FALLBACK_BETA in request.headers["anthropic-beta"]
    else:
        assert "fallbacks" not in sent
        assert FALLBACK_BETA not in request.headers.get("anthropic-beta", "")


async def test_completion_parsing(make_client):
    client = make_client(
        text_reply(
            "a",
            "b",
            thinking=True,
            usage={
                "input_tokens": 10,
                "output_tokens": 20,
                "cache_read_input_tokens": 5,
                "cache_creation_input_tokens": 3,
            },
        )
    )
    c = await client.complete(CompletionRequest("claude-opus-5-5", "SYS", "hi"))
    assert (c.text, c.input_tokens, c.output_tokens, c.cache_read_tokens, c.cache_write_tokens) == (
        "ab",
        10,
        20,
        5,
        3,
    )
    assert (c.model, c.stop_reason, c.refusal_category, c.json) == (
        "claude-opus-5-5",
        "end_turn",
        None,
        None,
    )
    assert c.latency_ms >= 0
    assert c.cost_usd == cost_usd("claude-opus-5-5", 10, 20, 5, 3)


async def test_json_parsed_when_schema_given(make_client):
    client = make_client(text_reply('{"a": 1}'))
    c = await client.complete(CompletionRequest("claude-opus-5-5", "", "q", output_schema={}))
    assert c.json == {"a": 1}


async def test_truncated_json_is_none_not_an_error(make_client):
    client = make_client(text_reply('{"a": ', stop_reason="max_tokens"))
    c = await client.complete(CompletionRequest("claude-opus-5-5", "", "q", output_schema={}))
    assert (c.stop_reason, c.text, c.json) == ("max_tokens", '{"a": ', None)


async def test_refusal_maps_category(make_client):
    client = make_client(
        text_reply(stop_reason="refusal", stop_details={"type": "refusal", "category": "cyber"})
    )
    c = await client.complete(CompletionRequest("claude-opus-5-5", "SYS", "hi"))
    assert (c.stop_reason, c.refusal_category, c.text) == ("refusal", "cyber", "")


async def test_cost_follows_the_model_that_answered(make_client):
    # server-side fallback can answer with another model; bill that one, not the requested one
    client = make_client(text_reply("ok", model="claude-sonnet-5-5"))
    c = await client.complete(
        CompletionRequest("claude-opus-5-5", "SYS", "hi", allow_fallback=True)
    )
    assert c.model == "claude-sonnet-5-5"
    assert c.cost_usd == cost_usd("claude-sonnet-5-5", 1, 1)


async def test_unknown_answering_model_falls_back_to_requested(make_client):
    client = make_client(text_reply("ok", model="claude-future-9"))
    c = await client.complete(
        CompletionRequest("claude-opus-5-5", "SYS", "hi", allow_fallback=True)
    )
    assert c.model == "claude-opus-5-5"


async def test_count_tokens(captured, make_client):
    client = make_client({"input_tokens": 42})
    n = await client.count_tokens(CompletionRequest("claude-opus-5-5", "SYS", "hi"))
    assert n == 42
    sent = body(captured)
    assert (sent["model"], sent["system"], sent["messages"]) == (
        "claude-opus-5-5",
        "SYS",
        [{"role": "user", "content": "hi"}],
    )
    assert captured[-1].url.path == "/v1/messages/count_tokens"


async def test_fake_is_deterministic():
    fake = FakeLLMClient({"q": '{"a": 1}'})
    req = CompletionRequest("claude-haiku-5-5", "", "q", output_schema={"type": "object"})
    c = await fake.complete(req)
    assert c.json == {"a": 1} and c.input_tokens == 100
    assert (c.text, c.output_tokens, c.cache_read_tokens, c.cache_write_tokens) == (
        '{"a": 1}',
        50,
        0,
        0,
    )
    assert (c.model, c.stop_reason, c.refusal_category, c.latency_ms) == (
        "claude-haiku-5-5",
        "end_turn",
        None,
        1,
    )
    assert fake.calls == [req]


async def test_fake_echoes_unknown_input_without_json():
    fake = FakeLLMClient()
    c = await fake.complete(CompletionRequest("claude-haiku-5-5", "sys", "hello"))
    assert (c.text, c.json) == ("hello", None)
    assert await fake.count_tokens(CompletionRequest("m", "abcd", "efgh1234")) == 3


async def test_provider_fake_backend(settings: Settings):
    container = build_container(settings.model_copy(update={"evals_llm_backend": "fake"}))
    try:
        assert isinstance(await container.get(LLMClient), FakeLLMClient)
    finally:
        await container.close()


async def test_provider_anthropic_backend(settings: Settings):
    container = build_container(settings.model_copy(update={"anthropic_api_key": "k"}))
    llm = await container.get(LLMClient)
    assert isinstance(llm, AnthropicLLMClient)
    inner = llm.client
    await container.close()
    assert inner.is_closed()


def test_settings_defaults(settings: Settings):
    assert settings.anthropic_api_key == ""
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.evals_run_cost_limit_usd == Decimal("5")
    assert settings.evals_concurrency == 4
    assert settings.evals_llm_backend == "anthropic"
    assert settings.content_dir == "../../content"
