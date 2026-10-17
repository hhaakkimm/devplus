from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GitHubUser:
    id: int
    login: str
    name: str | None
    avatar_url: str | None


class GitHubClient(Protocol):
    async def exchange_code(self, code: str) -> str: ...

    async def get_user(self, access_token: str) -> GitHubUser: ...
