"""Thin client of the internal LLM gateway."""

import json
import logging
import urllib.request
from dataclasses import dataclass, field

from config import Settings

log = logging.getLogger("assistant.llm")

MAX_RETRIES = 5


class LLMError(Exception):
    pass


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Reply:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def complete(self, messages: list[dict], tools: list[dict]) -> Reply:
        body = json.dumps(
            {
                "model": self._settings.model,
                "max_tokens": self._settings.max_tokens,
                "messages": messages,
                "tools": tools,
            }
        ).encode()
        request = urllib.request.Request(
            self._settings.api_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self._settings.api_key}",
                "Content-Type": "application/json",
            },
        )
        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    return self._parse(json.load(response))
            except Exception as e:
                log.warning("LLM call failed (attempt %d): %s", attempt + 1, e)
        raise LLMError("LLM gateway is unavailable")

    @staticmethod
    def _parse(data: dict) -> Reply:
        message = data["choices"][0]["message"]
        calls = [
            ToolCall(c["id"], c["name"], json.loads(c["arguments"]))
            for c in message.get("tool_calls") or []
        ]
        return Reply(text=message.get("content") or "", tool_calls=calls)
