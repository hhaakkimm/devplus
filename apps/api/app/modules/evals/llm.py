import json
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

import anthropic

from app.modules.evals import pricing

FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass(frozen=True)
class CompletionRequest:
    model: str
    system: str
    user: str
    effort: str = "medium"
    max_tokens: int = 1024
    output_schema: dict[str, Any] | None = None
    allow_fallback: bool = False


@dataclass(frozen=True)
class Completion:
    model: str
    text: str
    json: Any | None
    stop_reason: str
    refusal_category: str | None
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    latency_ms: int

    @property
    def cost_usd(self) -> Decimal:
        return pricing.cost_usd(
            self.model,
            self.input_tokens,
            self.output_tokens,
            self.cache_read_tokens,
            self.cache_write_tokens,
        )


class LLMClient(Protocol):
    async def complete(self, req: CompletionRequest) -> Completion: ...

    async def count_tokens(self, req: CompletionRequest) -> int: ...


class AnthropicLLMClient:
    def __init__(self, client: anthropic.AsyncAnthropic) -> None:
        self.client = client

    async def complete(self, req: CompletionRequest) -> Completion:
        output_config: dict[str, Any] = {"effort": req.effort}
        if req.output_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": req.output_schema}
        params: dict[str, Any] = {
            "model": req.model,
            "max_tokens": req.max_tokens,
            "messages": [{"role": "user", "content": req.user}],
            "thinking": {"type": "adaptive"},
            "output_config": output_config,
        }
        if req.system:  # the API rejects an empty text block
            params["system"] = [
                {"type": "text", "text": req.system, "cache_control": {"type": "ephemeral"}}
            ]
        started = time.monotonic()
        # Haiku has no server-side fallback, so never ask for one
        if req.allow_fallback and not req.model.startswith("claude-haiku"):
            msg = await self.client.beta.messages.create(
                **params, betas=[FALLBACK_BETA], fallbacks="default"
            )
        else:
            msg = await self.client.messages.create(**params)
        latency_ms = int((time.monotonic() - started) * 1000)

        text = "".join(b.text for b in msg.content if b.type == "text")
        # A fallback bills every attempt, while top-level usage covers only the serving one.
        # shortcut: summed hops are priced at the answering model's rates, though a declined hop
        # may have run on another model; switch to per-hop pricing if fallbacks become routine.
        hops = getattr(msg.usage, "iterations", None) or [msg.usage]
        return Completion(
            # a fallback may answer on another model: bill that one, if its price is known
            model=msg.model if msg.model in pricing.PRICES else req.model,
            text=text,
            json=_parse_json(text) if req.output_schema is not None else None,
            stop_reason=msg.stop_reason or "",
            refusal_category=msg.stop_details.category if msg.stop_details else None,
            input_tokens=sum(h.input_tokens for h in hops),
            output_tokens=sum(h.output_tokens for h in hops),
            cache_read_tokens=sum(h.cache_read_input_tokens or 0 for h in hops),
            cache_write_tokens=sum(h.cache_creation_input_tokens or 0 for h in hops),
            latency_ms=latency_ms,
        )

    async def count_tokens(self, req: CompletionRequest) -> int:
        params: dict[str, Any] = {
            "model": req.model,
            "messages": [{"role": "user", "content": req.user}],
        }
        if req.system:
            params["system"] = req.system
        return (await self.client.messages.count_tokens(**params)).input_tokens


def _parse_json(text: str) -> Any | None:
    # truncated (max_tokens) and refused responses carry no complete JSON
    try:
        return json.loads(text)
    except ValueError:
        return None


def _sample(schema: dict[str, Any], echo: str) -> Any:
    """A value of the schema's shape: strings echo the request, an enum gives its first value and
    an array has an item per value of the first enum its items have, so a checklist is complete."""
    if "enum" in schema:
        return schema["enum"][0]
    match schema.get("type"):
        case "object":
            return {k: _sample(v, echo) for k, v in schema.get("properties", {}).items()}
        case "array":
            item = schema["items"]
            sample = _sample(item, echo)
            enums = [(k, p["enum"]) for k, p in item.get("properties", {}).items() if "enum" in p]
            if not enums:
                return [sample]
            key, values = enums[0]
            return [{**sample, key: value} for value in values]
        case _:
            return echo


@dataclass
class FakeLLMClient:
    """Deterministic stand-in for tests and e2e: answers from `responses[req.user]`, else a value
    of the response schema if the request has one, else echoes."""

    responses: dict[str, str] | None = None
    calls: list[CompletionRequest] = field(default_factory=list)

    async def complete(self, req: CompletionRequest) -> Completion:
        self.calls.append(req)
        text = (self.responses or {}).get(req.user)
        if text is None and req.output_schema is not None:
            text = json.dumps(_sample(req.output_schema, req.user), ensure_ascii=False)
        if text is None:
            text = req.user
        return Completion(
            model=req.model,
            text=text,
            json=json.loads(text) if req.output_schema is not None else None,
            stop_reason="end_turn",
            refusal_category=None,
            input_tokens=100,
            output_tokens=50,
            cache_read_tokens=0,
            cache_write_tokens=0,
            latency_ms=1,
        )

    async def count_tokens(self, req: CompletionRequest) -> int:
        return (len(req.system) + len(req.user)) // 4
