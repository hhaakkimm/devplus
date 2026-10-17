import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import Forbidden, Unauthorized
from app.modules.auth.github import GitHubUser
from app.modules.auth.models import User, UserSession

SESSION_COOKIE = "session"
SESSION_TTL = timedelta(days=30)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    login: str
    name: str | None
    avatar_url: str | None


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def is_allowed(self, login: str) -> bool:
        return login.lower() in self.settings.allowed_logins

    async def upsert_user(self, gh: GitHubUser) -> CurrentUser:
        new = insert(User).values(
            github_id=gh.id, login=gh.login, name=gh.name, avatar_url=gh.avatar_url
        )
        stmt = new.on_conflict_do_update(
            index_elements=[User.github_id],
            set_={
                "login": new.excluded.login,
                "name": new.excluded.name,
                "avatar_url": new.excluded.avatar_url,
            },
        ).returning(User.id, User.login, User.name, User.avatar_url)
        row = (await self.session.execute(stmt)).one()
        await self.session.commit()
        return CurrentUser(*row)

    async def create_session(self, user_id: UUID) -> str:
        token = secrets.token_urlsafe(32)
        await self.session.execute(
            insert(UserSession).values(
                token_hash=hash_token(token),
                user_id=user_id,
                expires_at=func.now() + SESSION_TTL,
            )
        )
        await self.session.commit()
        return token

    async def current_user(self, token: str | None) -> CurrentUser:
        if not token:
            raise Unauthorized("Not authenticated")
        user = await self.session.scalar(
            select(User)
            .join(UserSession, UserSession.user_id == User.id)
            .where(UserSession.token_hash == hash_token(token), UserSession.expires_at > func.now())
        )
        if user is None:
            raise Unauthorized("Not authenticated")
        if not self.is_allowed(user.login):
            raise Forbidden("Access revoked")
        return CurrentUser(user.id, user.login, user.name, user.avatar_url)

    async def logout(self, token: str | None) -> None:
        if not token:
            return
        await self.session.execute(
            delete(UserSession).where(UserSession.token_hash == hash_token(token))
        )
        await self.session.commit()
