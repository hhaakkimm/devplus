from decimal import Decimal
from functools import cache
from typing import Literal

from pydantic_settings import BaseSettings


@cache
def _parse_logins(raw: str) -> frozenset[str]:
    parts = (p.strip().lower() for p in raw.split(","))
    return frozenset(p for p in parts if p)


class Settings(BaseSettings):
    """Read from environment variables only (no env_file: make exports .env)."""

    database_url: str
    github_client_id: str
    github_client_secret: str
    allowed_github_logins: str = ""
    app_origin: str
    cookie_secure: bool = True
    anthropic_api_key: str = ""
    redis_url: str = "redis://localhost:6379/0"
    evals_run_cost_limit_usd: Decimal = Decimal("5")
    evals_concurrency: int = 4
    evals_llm_backend: Literal["anthropic", "fake"] = "anthropic"
    content_dir: str = "../../content"

    # shortcut: allowlist lives in env; replace with open registration at public launch
    @property
    def allowed_logins(self) -> frozenset[str]:
        # cached per raw value, not per instance: model_copy would carry a stale cached_property
        return _parse_logins(self.allowed_github_logins)
