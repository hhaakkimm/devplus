import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import UUID

from sqlalchemy import ColumnElement, and_, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import BadRequest, Forbidden, NotFound, Unauthorized
from app.modules.auth.github import GitHubClient, GitHubUser
from app.modules.auth.models import TelegramLinkRequest, User, UserSession
from app.modules.auth.telegram import TelegramUser, verify_init_data

SESSION_COOKIE = "session"
STATE_COOKIE = "oauth_state"
TG_LINK_COOKIE = "tg_link"
SESSION_TTL = timedelta(days=30)
LINK_TTL = timedelta(minutes=10)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def live_link(token: str) -> ColumnElement[bool]:
    """The link request named by this token, while it has not expired."""
    return and_(
        TelegramLinkRequest.token_hash == hash_token(token),
        TelegramLinkRequest.expires_at > func.now(),
    )


@dataclass(frozen=True)
class LinkPending:
    telegram_id: int
    first_name: str
    username: str | None
    login: str


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

    async def user_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.session.scalar(select(User).where(User.telegram_id == telegram_id))

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


class GitHubLogin:
    def __init__(self, github: GitHubClient, auth: AuthService, settings: Settings) -> None:
        self.github = github
        self.auth = auth
        self.settings = settings

    def authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self.settings.github_client_id,
                "redirect_uri": f"{self.settings.app_origin}/api/auth/github/callback",
                "scope": "read:user",
                "state": state,
            }
        )
        return f"https://github.com/login/oauth/authorize?{query}"

    async def complete_login(self, code: str) -> str | None:
        gh = await self.github.get_user(await self.github.exchange_code(code))
        if not self.auth.is_allowed(gh.login):
            return None
        user = await self.auth.upsert_user(gh)
        return await self.auth.create_session(user.id)

    async def complete_link(self, code: str, token: str) -> str:
        """Bind a link request to the GitHub user and return the secret that confirms it.

        The link token is known to whoever made the link, so it is replaced: only the browser
        that passed GitHub gets the new secret and can confirm.
        """
        gh = await self.github.get_user(await self.github.exchange_code(code))
        session = self.auth.session
        if not self.auth.is_allowed(gh.login):
            await session.execute(
                delete(TelegramLinkRequest).where(
                    TelegramLinkRequest.token_hash == hash_token(token)
                )
            )
            await session.commit()
            raise BadRequest("not_allowed")
        user = await self.auth.upsert_user(gh)
        secret = secrets.token_urlsafe(32)
        bound = await session.scalar(
            update(TelegramLinkRequest)
            .where(live_link(token), TelegramLinkRequest.user_id.is_(None))
            .values(user_id=user.id, token_hash=hash_token(secret))
            .returning(TelegramLinkRequest.user_id)
        )
        await session.commit()
        if bound is None:
            raise BadRequest("invalid")
        return secret


class TelegramLogin:
    def __init__(self, auth: AuthService, settings: Settings) -> None:
        self.auth = auth
        self.settings = settings

    def require_configured(self) -> None:
        if not self.settings.telegram_bot_token:
            raise NotFound("Telegram login is not configured")

    def verify(self, init_data: str) -> TelegramUser:
        self.require_configured()
        return verify_init_data(init_data, self.settings.telegram_bot_token, datetime.now(UTC))

    async def login(self, init_data: str) -> tuple[str, CurrentUser]:
        tg = self.verify(init_data)
        user = await self.auth.user_by_telegram_id(tg.id)
        if user is None:
            raise NotFound("Telegram not linked")
        if not self.auth.is_allowed(user.login):
            raise Forbidden("Access revoked")
        # shortcut: a new 30-day session per Mini App launch, old ones are never cleaned up; add a
        # cleanup of expired sessions when the sessions table grows (20 users, fine for now)
        token = await self.auth.create_session(user.id)
        return token, CurrentUser(user.id, user.login, user.name, user.avatar_url)

    async def start_link(self, init_data: str) -> str:
        tg = self.verify(init_data)
        token = secrets.token_urlsafe(32)
        session = self.auth.session
        # shortcut: expired requests are swept on write, move it to a background job if the
        # table grows
        await session.execute(
            delete(TelegramLinkRequest).where(TelegramLinkRequest.expires_at <= func.now())
        )
        await session.execute(
            insert(TelegramLinkRequest).values(
                token_hash=hash_token(token),
                telegram_id=tg.id,
                first_name=tg.first_name,
                username=tg.username,
                expires_at=func.now() + LINK_TTL,
            )
        )
        await session.commit()
        return f"{self.settings.app_origin}/api/auth/telegram/link?token={token}"

    async def open_link(self, token: str) -> None:
        self.require_configured()
        opened = await self.auth.session.scalar(
            select(TelegramLinkRequest.token_hash).where(
                live_link(token), TelegramLinkRequest.user_id.is_(None)
            )
        )
        if opened is None:
            raise BadRequest("invalid")

    async def pending(self, token: str) -> LinkPending:
        self.require_configured()
        R = TelegramLinkRequest
        # the inner join drops requests whose GitHub step is not done (user_id is NULL)
        row = (
            await self.auth.session.execute(
                select(R.telegram_id, R.first_name, R.username, User.login)
                .join(User, User.id == R.user_id)
                .where(live_link(token))
            )
        ).one_or_none()
        if row is None:
            raise NotFound("Link request not found")
        return LinkPending(*row)

    async def confirm(self, token: str, telegram_id: int) -> None:
        """Bind the Telegram the confirmation page showed (`telegram_id`) to the request's user."""
        self.require_configured()
        session = self.auth.session
        # one statement takes the request, so two confirms of one token cannot both pass
        row = (
            await session.execute(
                delete(TelegramLinkRequest)
                .where(live_link(token), TelegramLinkRequest.user_id.is_not(None))
                .returning(TelegramLinkRequest.telegram_id, TelegramLinkRequest.user_id)
            )
        ).one_or_none()
        if row is None:
            raise NotFound("Link request not found")
        if row.telegram_id != telegram_id:
            # tg_link was swapped after the page loaded (another link went through this
            # browser): spend that request too, so a reload cannot offer it for a second try
            await session.commit()
            raise BadRequest("Telegram does not match the confirmation")
        user_id = row.user_id
        owner = await self.auth.user_by_telegram_id(telegram_id)
        linked = owner is None or owner.id == user_id
        if linked:
            try:
                # a concurrent confirm may take the id after the check: the unique index decides
                async with session.begin_nested():
                    await session.execute(
                        update(User).where(User.id == user_id).values(telegram_id=telegram_id)
                    )
            except IntegrityError:
                linked = False
        await session.commit()  # the request is spent whatever the outcome
        if not linked:
            raise BadRequest("Telegram is linked to another account")
