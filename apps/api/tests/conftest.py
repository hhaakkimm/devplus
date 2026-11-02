import asyncio
import json
import os
import zlib
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from dishka import Provider, Scope, provide
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.core.db import Base
from app.factory import create_app
from app.modules.auth.github import GitHubClient, GitHubUser
from app.modules.auth.service import SESSION_COOKIE, AuthService, CurrentUser
from app.modules.evals.executor import RunExecutor
from app.modules.evals.llm import FakeLLMClient, LLMClient
from app.modules.evals.models import Prompt, PromptVersion, Run
from app.modules.evals.queue import RunQueue
from app.modules.review.critic import critic_user
from app.modules.review.schemas import SECTION_NAMES

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://devplus:devplus@localhost:5432/devplus_test"
)


@pytest.fixture(scope="session", autouse=True)
def _schema() -> None:
    async def reset() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(reset())


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    # make exports the developer's .env, so unset fields would take its values, not the defaults
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    return Settings(
        database_url=TEST_DATABASE_URL,
        github_client_id="cid",
        github_client_secret="csecret",
        allowed_github_logins="Alice, bob ,,",
        app_origin="http://testserver",
        cookie_secure=False,
    )


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    # each test runs in one outer transaction; app commits become savepoints
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(
        bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    yield session
    await session.close()
    await trans.rollback()
    await conn.close()
    await engine.dispose()


@dataclass
class FakeGitHub:
    user: GitHubUser = field(
        default_factory=lambda: GitHubUser(id=1, login="alice", name="Alice", avatar_url=None)
    )

    async def exchange_code(self, code: str) -> str:
        return "gh-token"

    async def get_user(self, access_token: str) -> GitHubUser:
        return self.user


@dataclass
class RecordingQueue:
    ids: list[UUID] = field(default_factory=list)

    async def enqueue(self, run_id: UUID) -> None:
        self.ids.append(run_id)


class TestOverrides(Provider):
    def __init__(
        self,
        session: AsyncSession,
        github: GitHubClient,
        llm: LLMClient,
        queue: RunQueue,
    ) -> None:
        super().__init__()
        self._session = session
        self._github = github
        self._llm = llm
        self._queue = queue

    @provide(scope=Scope.REQUEST, override=True)
    def session(self) -> AsyncSession:
        return self._session

    @provide(scope=Scope.APP, override=True)
    def github(self) -> GitHubClient:
        return self._github

    @provide(scope=Scope.APP, override=True)
    def llm(self) -> LLMClient:
        return self._llm

    @provide(scope=Scope.APP, override=True)
    def queue(self) -> RunQueue:
        return self._queue


@pytest.fixture
def fake_github() -> FakeGitHub:
    return FakeGitHub()


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def fake_llm_critic(fake_llm: FakeLLMClient) -> Callable[..., dict[str, Any]]:
    """Scripts the critic's answer for one prompt and returns it.

    `script(system, user_template, rewritten=None, **reply)`: by default the critic grades every
    section 3, finds one issue and rewrites the system prompt, keeping the template as it is.
    `rewritten` overrides its parts, `reply` overrides top-level keys such as `sections`.
    """

    def script(
        system: str, user_template: str, rewritten: dict[str, str] | None = None, **reply: Any
    ) -> dict[str, Any]:
        answer: dict[str, Any] = {
            "sections": [{"name": n, "score": 3, "comment": f"{n}: слабо"} for n in SECTION_NAMES],
            "issues": [{"severity": "medium", "text": "Нет формата ответа"}],
            "rewritten": {
                "system": system + " Отвечай кратко.",
                "user_template": user_template,
                **(rewritten or {}),
            },
        } | reply
        fake_llm.responses = {
            **(fake_llm.responses or {}),
            critic_user(system, user_template): json.dumps(answer),
        }
        return answer

    return script


@pytest.fixture
def queue() -> RecordingQueue:
    return RecordingQueue()


@pytest.fixture
def overrides(
    db_session: AsyncSession,
    fake_github: FakeGitHub,
    fake_llm: FakeLLMClient,
    queue: RecordingQueue,
) -> list[Provider]:
    return [TestOverrides(db_session, fake_github, fake_llm, queue)]


@pytest.fixture
def app(settings: Settings, overrides: list[Provider]) -> FastAPI:
    return create_app(settings, *overrides)


@pytest.fixture
async def client(app: FastAPI, settings: Settings) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers={"Origin": settings.app_origin}
    ) as c:
        yield c


@pytest.fixture
def sign_in(client, db_session, settings):
    async def _sign_in(login: str = "alice") -> CurrentUser:
        auth = AuthService(db_session, settings)
        gh = GitHubUser(
            id=zlib.crc32(login.encode()), login=login, name=login.title(), avatar_url=None
        )
        user = await auth.upsert_user(gh)
        client.cookies.set(SESSION_COOKIE, await auth.create_session(user.id))
        return user

    return _sign_in


async def github_login(client: AsyncClient) -> Response:
    await client.get("/api/auth/github/login")
    return await client.get(
        f"/api/auth/github/callback?code=x&state={client.cookies['oauth_state']}"
    )


@pytest.fixture
def run_executor(
    db_session: AsyncSession, fake_llm: FakeLLMClient, settings: Settings
) -> RunExecutor:
    return RunExecutor(db_session, fake_llm, settings)


@pytest.fixture
def make_run(db_session: AsyncSession, settings: Settings) -> Callable[..., Awaitable[Run]]:
    """A queued run with its prompt, version and case snapshot, written straight to the session.

    `cases` are `{"variables": ..., "expected": ...}` dicts, numbered from 1 like a real snapshot.
    The default template echoes `{{name}}`, which the fake LLM answers with `name` itself.
    """

    async def make(
        cases: list[dict[str, Any]] | None = None,
        graders: list[dict[str, Any]] | None = None,
        *,
        template: str = "{{name}}",
        model: str = "claude-haiku-5-5",
        source: str = "lab",
        cost_limit_usd: str = "1",
        pass_threshold: str | None = None,
        status: str = "queued",
    ) -> Run:
        cases = cases or [
            {"variables": {"name": "a"}, "expected": "a"},
            {"variables": {"name": "b"}, "expected": "b"},
        ]
        gh = GitHubUser(id=zlib.crc32(b"alice"), login="alice", name="Alice", avatar_url=None)
        user = await AuthService(db_session, settings).upsert_user(gh)
        prompt = Prompt(owner_id=user.id, name="P")
        db_session.add(prompt)
        await db_session.flush()
        version = PromptVersion(
            prompt_id=prompt.id,
            number=1,
            system="s",
            user_template=template,
            model=model,
            effort="medium",
            max_tokens=1024,
            output_schema=None,
            created_by=user.id,
        )
        db_session.add(version)
        await db_session.flush()
        run = Run(
            owner_id=user.id,
            prompt_version_id=version.id,
            source=source,
            graders=graders or [{"type": "exact"}],
            cases=[{"position": i, **c} for i, c in enumerate(cases, 1)],
            status=status,
            cost_limit_usd=Decimal(cost_limit_usd),
            estimated_cost_usd=Decimal(0),
            cases_total=len(cases),
            pass_threshold=None if pass_threshold is None else Decimal(pass_threshold),
        )
        db_session.add(run)
        await db_session.commit()
        return run

    return make
