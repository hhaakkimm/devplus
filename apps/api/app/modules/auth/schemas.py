from uuid import UUID

from pydantic import BaseModel


class MeOut(BaseModel):
    id: UUID
    login: str
    name: str | None
    avatar_url: str | None


class TelegramInitIn(BaseModel):
    init_data: str


class TelegramLinkOut(BaseModel):
    url: str


class TelegramLinkConfirmIn(BaseModel):
    telegram_id: int  # the Telegram that pending showed: confirm binds only that one


class TelegramUserOut(BaseModel):
    id: int
    first_name: str
    username: str | None


class TelegramLinkPendingOut(BaseModel):
    telegram: TelegramUserOut
    login: str
