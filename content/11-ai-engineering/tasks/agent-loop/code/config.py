"""Settings of the internal assistant, read once at start-up."""

import os
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path(os.environ.get("ASSISTANT_WORKSPACE", ".")).resolve()


@dataclass(frozen=True)
class Settings:
    api_url: str
    api_key: str
    model: str
    max_tokens: int = 1024


def load_settings() -> Settings:
    # no default for the key: better to crash at start-up than to fail on the first question
    return Settings(
        api_url=os.environ.get("LLM_API_URL", "https://llm.internal.example/v1/chat"),
        api_key=os.environ["LLM_API_KEY"],
        model=os.environ.get("LLM_MODEL", "assistant-large"),
    )
