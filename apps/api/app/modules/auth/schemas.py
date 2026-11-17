from uuid import UUID

from pydantic import BaseModel


class MeOut(BaseModel):
    id: UUID
    login: str
    name: str | None
    avatar_url: str | None


class TelegramInitIn(BaseModel):
    init_data: str
