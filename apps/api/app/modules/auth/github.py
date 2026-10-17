from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import Settings
from app.core.errors import BadRequest


@dataclass(frozen=True)
class GitHubUser:
    id: int
    login: str
    name: str | None
    avatar_url: str | None


class GitHubClient(Protocol):
    async def exchange_code(self, code: str) -> str: ...

    async def get_user(self, access_token: str) -> GitHubUser: ...


class HttpGitHubClient:
    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self.http = http
        self.settings = settings

    async def exchange_code(self, code: str) -> str:
        r = await self.http.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": self.settings.github_client_id,
                "client_secret": self.settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token = r.json().get("access_token")
        if not token:
            raise BadRequest("GitHub login failed")
        return str(token)

    async def get_user(self, access_token: str) -> GitHubUser:
        r = await self.http.get(
            "https://api.github.com/user", headers={"Authorization": f"Bearer {access_token}"}
        )
        if not r.is_success:
            raise BadRequest("GitHub login failed")
        data = r.json()
        return GitHubUser(data["id"], data["login"], data["name"], data["avatar_url"])
