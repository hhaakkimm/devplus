# devplus: минимальное ядро. План реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Каркас платформы. Участник команды входит через GitHub, видит программу обучения, читает урок в MDX и отмечает его пройденным. Всё работает локально (`make dev`), проверяется в CI и деплоится на VPS.

**Architecture:**
- Модульный монолит: FastAPI (`apps/api`) с модулями `auth` и `progress` и DI через dishka, плюс Next.js 16 (`apps/web`), который читает уроки из `content/` и ходит в API через TS-клиент, сгенерированный из OpenAPI.
- В проде Caddy держит один origin: `/api/*` → api, остальное → web.

**Tech Stack:**
- Python 3.13, uv 0.9, FastAPI 0.143, Pydantic v2, SQLAlchemy 2.1 (asyncio, asyncpg), Alembic 1.20, dishka 1.10, httpx 0.28, pytest 9 + pytest-asyncio 1.4, ruff, mypy, import-linter.
- Node 24, pnpm 10, Next.js 16.4, React 19, Tailwind 4, shadcn/ui, next-mdx-remote 6, gray-matter, openapi-typescript 7 + openapi-fetch 0.17, Vitest 5, Playwright 1.64.
- PostgreSQL 17, Caddy 2, GitHub Actions, GHCR.

**Spec:** `docs/superpowers/specs/2026-10-18-devplus-overview-core-design.md`, разделы 2, 3 и 5.

## Global Constraints

**DI и модули**
- DI только через dishka (`DishkaRoute` + `FromDishka`). Сервисы не собираются через цепочки FastAPI `Depends`.
- Модуль бэкенда = `router.py`, `service.py`, `models.py`, `schemas.py`, `providers.py` в `apps/api/app/modules/<name>/`.
- Из другого модуля импортируется только `service`. Правило проверяет import-linter.

**Ошибки**
- Ответ при ошибке: `{"detail": "..."}`. Валидация остаётся стандартной 422.
- Непредвиденная ошибка: 500 `{"detail": "Internal Server Error"}`, stack trace и `request_id` пишутся в лог.

**Сессии и вход**
- Cookie `session`: `HttpOnly`, `Secure` = `COOKIE_SECURE`, `SameSite=Lax`, `Path=/`, срок 30 дней.
- Токен `secrets.token_urlsafe(32)`, в БД лежит только SHA-256 hex. Просроченная сессия равна отсутствию сессии.
- Методы POST, PUT, PATCH, DELETE принимаются только с `Origin == APP_ORIGIN`, иначе 403 `{"detail": "Origin not allowed"}`.
- `ALLOWED_GITHUB_LOGINS`: логины через запятую, без учёта регистра, пробелы и пустые элементы игнорируются.

**Прогресс**
- Slug урока: `^[a-z0-9-]+/[a-z0-9-]+$`, не длиннее 200 символов.

**Конфигурация**
- Переменные окружения ядра: `DATABASE_URL`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `ALLOWED_GITHUB_LOGINS`, `APP_ORIGIN`, `COOKIE_SECURE`.
- Web добавляет `API_INTERNAL_URL` (dev: `http://localhost:8000`, prod: `http://api:8000`) и `CONTENT_DIR`.

**Интерфейс**
- Только русский язык. Тексты фиксированы в задачах, тесты на них опираются.

**ponytail**
- Минимальное полное изменение.
- Ровно два известных ограничения получают комментарий `shortcut:`:
  - список доступа в env (Task 2);
  - потеря прогресса при переименовании урока (Task 4).

**Процесс**
- Перед каждым коммитом зелёные `make lint` и `make test` для затронутой части.
- Выполненный шаг отмечается `- [x]` в этом файле и коммитится вместе с кодом задачи.

## Review Focus

1. **Пользователя убрали из `ALLOWED_GITHUB_LOGINS`, а у него живая сессия на 30 дней.** Каждый запрос с сессией заново проверяет список: 403 `Access revoked`, а web отправляет на `/no-access`. Тест в Task 2.
2. **Колбэк OAuth пришёл с `error=access_denied`, без `code`, с чужим `state` или без cookie `oauth_state`.** Ответ 400 `Invalid OAuth callback`, в БД не появляется ни пользователь, ни сессия. Тесты в Task 3.
3. **Значение `ALLOWED_GITHUB_LOGINS` с пробелами, регистром и пустыми элементами (`"Alice, bob ,,"`).** Получается `{"alice", "bob"}`. Пустая строка значит, что не пускаем никого. Тест в Task 2.
4. **Изменяющий запрос без заголовка `Origin` или с чужим `Origin`.** Ответ 403, состояние не меняется. GET без `Origin` работает. Тесты в Task 1 и Task 2.
5. **Плохой контент:** урок без `title`, модуль без `_module.json`, посторонние файлы в `content/`, прогресс по удалённому уроку. Загрузчик падает с ошибкой, в которой есть имя файла. Посторонние файлы игнорируются. Счётчики не учитывают отметки по несуществующим урокам. Тесты в Task 7.

## File Structure

```
.env.example                         # переменные для локальной разработки
Makefile                             # dev, db, api, web, test, lint, gen-client, migrate, e2e
package.json, pnpm-workspace.yaml    # pnpm workspace: apps/web, packages/api-client
README.md                            # локальный запуск, OAuth-приложение GitHub
apps/api/
  pyproject.toml, uv.lock, .python-version, alembic.ini, Dockerfile
  app/factory.py                     # create_app(settings, *overrides)
  app/main.py                        # app = create_app()  (точка входа uvicorn)
  app/core/config.py                 # Settings
  app/core/db.py                     # Base, DbProvider
  app/core/errors.py                 # DomainError и наследники, register_error_handlers
  app/core/logging.py                # JSON-логи, request_id
  app/core/security.py               # проверка Origin
  app/core/health.py                 # GET /api/health
  app/core/container.py              # build_container
  app/modules/auth/                  # models, github, service, schemas, router, providers
  app/modules/progress/              # models, service, schemas, router, providers
  migrations/                        # Alembic (async)
  scripts/seed_e2e.py                # пользователь и сессия для e2e
  tests/                             # conftest, test_core, test_auth_sessions, test_auth_github, test_progress
apps/web/                            # Next.js (create-next-app)
  lib/content.ts, lib/progress.ts, lib/api.ts, lib/browser-api.ts, lib/session.ts
  components/header.tsx, logout-button.tsx, progress-toggle.tsx
  app/(app)/layout.tsx, app/(app)/page.tsx, app/(app)/lessons/[module]/[lesson]/page.tsx
  app/no-access/page.tsx
  test/ (vitest), e2e/ (playwright), Dockerfile
packages/api-client/                 # openapi.json, src/schema.d.ts (генерируется), src/index.ts
content/00-start/                    # _module.json, 01-how-to-use.mdx
infra/docker-compose.dev.yml, infra/postgres-init.sql
infra/docker-compose.yml, infra/Caddyfile, infra/app.env.example
.github/workflows/ci.yml, deploy.yml, .github/dependabot.yml
docs/deploy.md
```

---

### Task 1: Каркас API, ядро и тестовая инфраструктура

**Files:**
- Create: `apps/api/pyproject.toml`, `apps/api/.python-version` (`3.13`), `apps/api/app/__init__.py`, `apps/api/app/factory.py`, `apps/api/app/main.py`, `apps/api/app/core/{__init__,config,db,errors,logging,security,health,container}.py`, `apps/api/app/modules/__init__.py`
- Create: `infra/docker-compose.dev.yml`, `infra/postgres-init.sql`, `.env.example`, `Makefile`, `README.md`
- Test: `apps/api/tests/conftest.py`, `apps/api/tests/test_core.py`

**Interfaces:**
- Produces:
  - `Settings(BaseSettings)` в `app.core.config`:
    - поля `database_url: str`, `github_client_id: str`, `github_client_secret: str`, `allowed_github_logins: str = ""`, `app_origin: str`, `cookie_secure: bool = True`;
    - только переменные окружения, без `env_file`.
  - `Base(DeclarativeBase)`, `DbProvider(Provider)` в `app.core.db`:
    - APP: `AsyncEngine` (генератор с `dispose`), `async_sessionmaker[AsyncSession]` (`expire_on_commit=False`);
    - REQUEST: `AsyncSession` (генератор, закрывает сессию).
  - `app.core.errors`:
    - `DomainError(Exception)` с атрибутом класса `status_code: int = 400`;
    - наследники `BadRequest` 400, `Unauthorized` 401, `Forbidden` 403, `NotFound` 404, `Conflict` 409;
    - `register_error_handlers(app: FastAPI) -> None`.
  - `app.core.logging`: `configure_logging(level: str = "INFO") -> None`, `install_request_id(app: FastAPI) -> None`. Заголовок `X-Request-ID` берётся из запроса или генерируется (`uuid4().hex`) и возвращается в ответе.
  - `app.core.security`: `install_origin_check(app: FastAPI, app_origin: str) -> None`.
  - `app.core.container`: `build_container(settings: Settings, *overrides: Provider) -> AsyncContainer`. Это `make_async_container(ConfigProvider(), DbProvider(), <провайдеры модулей>, FastapiProvider(), *overrides, context={Settings: settings})`. `ConfigProvider` содержит `from_context(provides=Settings, scope=Scope.APP)`.
  - `app.factory`: `create_app(settings: Settings | None = None, *overrides: Provider) -> FastAPI`. Подключает роутеры, обработчики ошибок, request id, проверку Origin и `setup_dishka`. В lifespan закрывает контейнер.
  - `app.main`: `app = create_app()`.

- [x] **Step 1: Окружение.**
  - `uv init --app` в `apps/api` либо `pyproject.toml` вручную, `requires-python = ">=3.13"`.
  - Зависимости: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`, `dishka`, `httpx`.
  - Dev-зависимости: `pytest`, `pytest-asyncio`, `ruff`, `mypy`, `import-linter`.
  - `[tool.pytest.ini_options] asyncio_mode = "auto"`.
  - `[tool.ruff] line-length = 100`, `lint.select = ["E","F","I","B","UP","ASYNC"]`.
  - `[tool.mypy] strict = true`, `plugins = ["pydantic.mypy"]`, `files = ["app"]`.
  - `infra/docker-compose.dev.yml`: сервис `postgres` (`postgres:17`, пользователь, пароль и база `devplus`, порт `5432`, healthcheck `pg_isready`, том). `infra/postgres-init.sql` с `CREATE DATABASE devplus_test;` монтируется в `/docker-entrypoint-initdb.d/`.
  - `.env.example`:

```
DATABASE_URL=postgresql+asyncpg://devplus:devplus@localhost:5432/devplus
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
ALLOWED_GITHUB_LOGINS=
APP_ORIGIN=http://localhost:3000
COOKIE_SECURE=false
API_INTERNAL_URL=http://localhost:8000
```

  - `Makefile`: `-include .env` + `export`. Цели:
    - `db`: `docker compose -f infra/docker-compose.dev.yml up -d --wait`;
    - `api`: `cd apps/api && uv run uvicorn app.main:app --reload --port 8000`;
    - `test-api`: `cd apps/api && uv run pytest`;
    - `lint-api`: `ruff check`, `ruff format --check`, `mypy`.
    - Агрегаты `test` и `lint` пока вызывают только api-цели.
  - `README.md`:
    - `make db`, `cp .env.example .env`, `make api`;
    - одна строка о том, что `.env` пишется без кавычек, потому что его читает make;
    - как создать локальное OAuth-приложение GitHub (Settings → Developer settings → OAuth Apps). Homepage `http://localhost:3000`, callback `http://localhost:3000/api/auth/github/callback`. Client ID и secret положить в `.env`.
  - Проверка: `make db && cd apps/api && uv sync`. Ожидается: Postgres healthy, зависимости установлены.

- [x] **Step 2: Написать `tests/conftest.py`.** Здесь задаётся, как работают все тесты API, поэтому код приведён целиком:

```python
import asyncio
import os
from collections.abc import AsyncIterator

import pytest
from dishka import Provider, Scope, provide
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.core.db import Base
from app.factory import create_app

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
def settings() -> Settings:
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
    session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    yield session
    await session.close()
    await trans.rollback()
    await conn.close()
    await engine.dispose()


class TestOverrides(Provider):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self._session = session

    @provide(scope=Scope.REQUEST, override=True)
    def session(self) -> AsyncSession:
        return self._session


@pytest.fixture
def overrides(db_session: AsyncSession) -> list[Provider]:
    return [TestOverrides(db_session)]


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
```

- [x] **Step 3: Написать падающие тесты в `tests/test_core.py`.**

```python
async def test_health_ok(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

async def test_health_reports_db_down(settings):
    class BrokenSession:
        async def execute(self, *a, **kw):
            raise OSError("db down")
    class Broken(Provider):
        @provide(scope=Scope.REQUEST, override=True)
        def session(self) -> AsyncSession:
            return BrokenSession()  # type: ignore[return-value]
    app = create_app(settings, Broken())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        r = await c.get("/api/health")
    assert r.status_code == 503
    assert r.json() == {"detail": "Database unavailable"}

async def test_domain_error_maps_to_status(app, client):
    async def boom():
        raise NotFound("Lesson not found")
    app.add_api_route("/api/_test/boom", boom)
    r = await client.get("/api/_test/boom")
    assert r.status_code == 404
    assert r.json() == {"detail": "Lesson not found"}

async def test_unexpected_error_is_generic_500(app, client, caplog):
    async def crash():
        raise RuntimeError("secret internals")
    app.add_api_route("/api/_test/crash", crash)
    r = await client.get("/api/_test/crash")
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal Server Error"}
    assert "secret internals" in caplog.text

async def test_request_id_is_echoed_or_generated(client):
    assert (await client.get("/api/health", headers={"X-Request-ID": "abc"})).headers["x-request-id"] == "abc"
    assert len((await client.get("/api/health")).headers["x-request-id"]) == 32

@pytest.mark.parametrize("origin", [None, "", "https://evil.example"])
async def test_mutation_with_wrong_origin_is_403(client, origin):
    headers = {} if origin is None else {"Origin": origin}
    client.headers.pop("Origin")
    r = await client.post("/api/health", headers=headers)
    assert r.status_code == 403
    assert r.json() == {"detail": "Origin not allowed"}

async def test_mutation_with_app_origin_passes_check(client):
    assert (await client.post("/api/health")).status_code == 405  # reaches routing

async def test_get_without_origin_is_allowed(client):
    client.headers.pop("Origin")
    assert (await client.get("/api/health")).status_code == 200
```

- [x] **Step 4: Запустить тесты, убедиться, что они падают.** Запуск: `make test-api`. Ожидается: ошибка импорта, модулей `app.*` ещё нет.

- [x] **Step 5: Реализовать `app/core/*`, `app/factory.py`, `app/main.py`** по интерфейсам выше.
  - Health: `router = APIRouter(prefix="/api", route_class=DishkaRoute)`. `GET /health` выполняет `select 1` через `FromDishka[AsyncSession]`. При `OSError` или `SQLAlchemyError` ответ 503.
  - Обработчик `Exception` пишет в лог через `logger.exception` и отвечает 500.
  - JSON-формат лога: `ts`, `level`, `logger`, `msg`, `request_id`, `exc_info`.

- [x] **Step 6: Запустить тесты и линтеры.** Запуск: `make test-api && make lint-api`. Ожидается: 10 passed, ruff и mypy чистые.

- [x] **Step 7: Commit**

```bash
git add Makefile README.md .env.example infra/docker-compose.dev.yml infra/postgres-init.sql apps/api docs/superpowers/plans/2026-10-18-devplus-core.md
git commit -m "feat(api): app skeleton with dishka container, errors, logging, origin check, health"
```

---

### Task 2: auth — пользователи, сессии, текущий пользователь, выход

**Files:**
- Create: `apps/api/app/modules/auth/{__init__,models,github,service,schemas,router,providers}.py`
- Modify: `apps/api/app/core/config.py` (свойство `allowed_logins`), `apps/api/app/core/container.py`, `apps/api/app/factory.py` (подключить провайдер и роутер)
- Test: `apps/api/tests/test_auth_sessions.py`, `apps/api/tests/conftest.py` (фикстура `sign_in`)

**Interfaces:**
- Consumes: `Settings`, `Base`, `AsyncSession`, `Unauthorized` и `Forbidden` из Task 1.
- Produces:
  - `Settings.allowed_logins -> frozenset[str]`, кэшируемое свойство.
  - Модели:
    - `User` (таблица `users`): `id: UUID` PK (`uuid4`), `github_id: int` (BigInteger, unique), `login: str`, `name: str | None`, `avatar_url: str | None`, `created_at` (server default `now()`);
    - `UserSession` (таблица `sessions`): `token_hash: str` PK, `user_id` FK → `users.id` `ON DELETE CASCADE`, `created_at`, `expires_at` (timestamptz).
  - `app.modules.auth.github`:
    - `@dataclass(frozen=True) GitHubUser(id: int, login: str, name: str | None, avatar_url: str | None)`;
    - `class GitHubClient(Protocol)` с методами `exchange_code(code: str) -> str` и `get_user(access_token: str) -> GitHubUser`, оба async. Реализация будет в Task 3.
  - `app.modules.auth.service`:
    - константы `SESSION_COOKIE = "session"`, `SESSION_TTL = timedelta(days=30)`;
    - `hash_token(token: str) -> str` (SHA-256 hex);
    - `@dataclass(frozen=True) CurrentUser(id: UUID, login: str, name: str | None, avatar_url: str | None)`;
    - `AuthService(session: AsyncSession, settings: Settings)`:
      - `upsert_user(gh: GitHubUser) -> CurrentUser`: по `github_id`, обновляет `login`, `name`, `avatar_url`;
      - `create_session(user_id: UUID) -> str`: возвращает сырой токен;
      - `current_user(token: str | None) -> CurrentUser`: бросает `Unauthorized("Not authenticated")` или `Forbidden("Access revoked")`;
      - `logout(token: str | None) -> None`;
      - `is_allowed(login: str) -> bool`.
  - `AuthProvider` (REQUEST):
    - `AuthService`;
    - `CurrentUser` = `await auth.current_user(request.cookies.get(SESSION_COOKIE))`, `Request` берётся из контекста `FastapiProvider`.
  - Эндпоинты:
    - `GET /api/me` → `MeOut{id, login, name, avatar_url}`;
    - `POST /api/auth/logout` → 204, удаляет cookie `session` (`path="/"`).

- [x] **Step 1: Фикстура `sign_in` в conftest.**

```python
@pytest.fixture
def sign_in(client, db_session, settings):
    async def _sign_in(login: str = "alice") -> CurrentUser:
        auth = AuthService(db_session, settings)
        gh = GitHubUser(id=zlib.crc32(login.encode()), login=login, name=login.title(), avatar_url=None)
        user = await auth.upsert_user(gh)
        client.cookies.set(SESSION_COOKIE, await auth.create_session(user.id))
        return user
    return _sign_in
```

- [x] **Step 2: Написать падающие тесты в `tests/test_auth_sessions.py`.**

```python
def test_allowlist_is_trimmed_and_case_insensitive(settings):
    assert settings.allowed_logins == frozenset({"alice", "bob"})
    assert settings.model_copy(update={"allowed_github_logins": ""}).allowed_logins == frozenset()

async def test_me_requires_session(client):
    r = await client.get("/api/me")
    assert r.status_code == 401
    assert r.json() == {"detail": "Not authenticated"}

async def test_me_returns_current_user(client, sign_in):
    user = await sign_in("alice")
    r = await client.get("/api/me")
    assert r.status_code == 200
    assert r.json() == {"id": str(user.id), "login": "alice", "name": "Alice", "avatar_url": None}

async def test_unknown_token_is_401(client):
    client.cookies.set("session", "nope")
    assert (await client.get("/api/me")).status_code == 401

async def test_expired_session_is_401(client, sign_in, db_session):
    await sign_in("alice")
    await db_session.execute(update(UserSession).values(expires_at=func.now() - timedelta(seconds=1)))
    assert (await client.get("/api/me")).status_code == 401

async def test_login_removed_from_allowlist_is_403(client, sign_in):
    await sign_in("carol")  # sign_in bypasses the allowlist, like a session created before removal
    r = await client.get("/api/me")
    assert r.status_code == 403
    assert r.json() == {"detail": "Access revoked"}

async def test_db_stores_only_token_hash(client, sign_in, db_session):
    await sign_in("alice")
    token = client.cookies["session"]
    stored = (await db_session.scalars(select(UserSession.token_hash))).one()
    assert stored == hash_token(token) != token

async def test_upsert_keeps_one_row_per_github_id(db_session, settings):
    auth = AuthService(db_session, settings)
    await auth.upsert_user(GitHubUser(id=1, login="alice", name="A", avatar_url=None))
    user = await auth.upsert_user(GitHubUser(id=1, login="alice2", name="B", avatar_url="https://x/a.png"))
    assert (user.login, user.name, user.avatar_url) == ("alice2", "B", "https://x/a.png")
    assert await db_session.scalar(select(func.count()).select_from(User)) == 1

async def test_logout_ends_session(client, sign_in, db_session):
    await sign_in("alice")
    r = await client.post("/api/auth/logout")
    assert r.status_code == 204
    assert "Max-Age=0" in r.headers["set-cookie"]
    assert await db_session.scalar(select(func.count()).select_from(UserSession)) == 0
    assert (await client.get("/api/me")).status_code == 401

async def test_logout_with_foreign_origin_keeps_session(client, sign_in):
    await sign_in("alice")
    r = await client.post("/api/auth/logout", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert (await client.get("/api/me")).status_code == 200
```

- [x] **Step 3: Запустить тесты, убедиться, что они падают.** Запуск: `make test-api`. Ожидается: ошибка импорта `app.modules.auth`.

- [x] **Step 4: Реализовать модуль `auth`** по интерфейсам выше.
  - Модели импортируются в `container.py` через провайдер, поэтому попадают в `Base.metadata` до `create_all`.
  - Рядом с `allowed_logins` в `config.py` комментарий: `# shortcut: allowlist lives in env; replace with open registration at public launch`.

- [x] **Step 5: Запустить тесты и линтеры.** Запуск: `make test-api && make lint-api`. Ожидается: всё зелёное.

- [x] **Step 6: Commit**

```bash
git add apps/api docs/superpowers/plans/2026-10-18-devplus-core.md
git commit -m "feat(api): auth module with users, hashed sessions, allowlist recheck, logout"
```

---

### Task 3: auth — вход через GitHub OAuth

**Files:**
- Modify: `apps/api/app/modules/auth/{github,service,router,providers}.py`
- Test: `apps/api/tests/test_auth_github.py`, `apps/api/tests/conftest.py` (`FakeGitHub`, подмена `GitHubClient`)

**Interfaces:**
- Consumes: `AuthService`, `GitHubUser`, `GitHubClient`, `BadRequest` из Task 1 и Task 2.
- Produces:
  - `HttpGitHubClient(http: httpx.AsyncClient, settings: Settings)`, реализует `GitHubClient`.
    - `exchange_code`: `POST https://github.com/login/oauth/access_token` с `client_id`, `client_secret`, `code` и `Accept: application/json`. Если в ответе нет `access_token`, бросает `BadRequest("GitHub login failed")`.
    - `get_user`: `GET https://api.github.com/user` с `Authorization: Bearer <token>`. Если статус не 2xx, бросает `BadRequest("GitHub login failed")`.
  - `GitHubLogin(github: GitHubClient, auth: AuthService, settings: Settings)` в `service.py`:
    - `authorize_url(state: str) -> str` даёт `https://github.com/login/oauth/authorize?client_id=…&redirect_uri={APP_ORIGIN}/api/auth/github/callback&scope=read:user&state=…`;
    - `complete_login(code: str) -> str | None` возвращает токен сессии. Если логина нет в списке, возвращает `None` и ничего не пишет в БД.
  - `STATE_COOKIE = "oauth_state"`: `HttpOnly`, `Secure` = `COOKIE_SECURE`, `SameSite=Lax`, `path="/api/auth"`, `max_age=600`.
  - `AuthProvider` получает:
    - APP: `httpx.AsyncClient` (генератор, `aclose`) и `GitHubClient` → `HttpGitHubClient`;
    - REQUEST: `GitHubLogin`.
  - Эндпоинты:
    - `GET /api/auth/github/login` → 302 на `authorize_url` и установка cookie `oauth_state`.
    - `GET /api/auth/github/callback?code&state&error`:
      - если есть `error`, нет `code`, нет `state` или `state` не совпадает с cookie: `BadRequest("Invalid OAuth callback")`;
      - логин не в списке: 302 на `/no-access`;
      - успешный вход: 302 на `/` и установка cookie `session`;
      - в обоих случаях с 302 cookie `oauth_state` удаляется.

- [x] **Step 1: `FakeGitHub` в conftest и подмена в `TestOverrides`.**
  - `TestOverrides(session, github)` получает второй провайдер: `GitHubClient` в области APP с `override=True`.
  - Фикстура `fake_github` возвращает `FakeGitHub()`.
  - Фикстура `overrides` возвращает `[TestOverrides(db_session, fake_github)]`.

```python
@dataclass
class FakeGitHub:
    user: GitHubUser = field(default_factory=lambda: GitHubUser(id=1, login="alice", name="Alice", avatar_url=None))
    async def exchange_code(self, code: str) -> str:
        return "gh-token"
    async def get_user(self, access_token: str) -> GitHubUser:
        return self.user

async def github_login(client) -> Response:
    await client.get("/api/auth/github/login")
    return await client.get(f"/api/auth/github/callback?code=x&state={client.cookies['oauth_state']}")
```

- [x] **Step 2: Написать падающие тесты в `tests/test_auth_github.py`.**

```python
async def test_login_redirects_to_github_with_state(client):
    r = await client.get("/api/auth/github/login")
    assert r.status_code == 302
    url = urlparse(r.headers["location"]); q = parse_qs(url.query)
    assert (url.netloc, url.path) == ("github.com", "/login/oauth/authorize")
    assert q["client_id"] == ["cid"]
    assert q["redirect_uri"] == ["http://testserver/api/auth/github/callback"]
    assert q["scope"] == ["read:user"]
    assert q["state"] == [client.cookies["oauth_state"]]

async def test_callback_signs_in_allowed_user(client):
    r = await github_login(client)
    assert (r.status_code, r.headers["location"]) == (302, "/")
    assert (await client.get("/api/me")).json()["login"] == "alice"

async def test_repeat_login_updates_profile(client, fake_github, db_session):
    await github_login(client)
    fake_github.user = replace(fake_github.user, login="Alice", name="Alice Renamed")
    await github_login(client)
    assert await db_session.scalar(select(func.count()).select_from(User)) == 1
    assert (await client.get("/api/me")).json()["name"] == "Alice Renamed"

async def test_login_outside_allowlist_goes_to_no_access(client, fake_github, db_session):
    fake_github.user = replace(fake_github.user, id=2, login="mallory")
    r = await github_login(client)
    assert r.headers["location"] == "/no-access"
    assert await db_session.scalar(select(func.count()).select_from(User)) == 0
    assert "session" not in client.cookies

@pytest.mark.parametrize("query", ["code=x&state=wrong", "state=STATE", "error=access_denied&state=STATE"])
async def test_bad_callback_is_400(client, db_session, query):
    await client.get("/api/auth/github/login")
    r = await client.get("/api/auth/github/callback?" + query.replace("STATE", client.cookies["oauth_state"]))
    assert r.status_code == 400
    assert r.json() == {"detail": "Invalid OAuth callback"}
    assert await db_session.scalar(select(func.count()).select_from(User)) == 0

async def test_callback_without_state_cookie_is_400(client):
    assert (await client.get("/api/auth/github/callback?code=x&state=s")).status_code == 400

async def test_http_client_maps_github_error(settings):
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"error": "bad_verification_code"}))
    async with httpx.AsyncClient(transport=transport) as http:
        with pytest.raises(BadRequest, match="GitHub login failed"):
            await HttpGitHubClient(http, settings).exchange_code("x")

async def test_http_client_reads_user(settings):
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.headers["authorization"] == "Bearer t"
        return httpx.Response(200, json={"id": 7, "login": "alice", "name": None, "avatar_url": "https://a/x.png"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        assert await HttpGitHubClient(http, settings).get_user("t") == GitHubUser(7, "alice", None, "https://a/x.png")
```

- [x] **Step 3: Запустить тесты, убедиться, что они падают.** Запуск: `make test-api`. Ожидается: 404 на `/api/auth/github/login`, ошибка импорта `HttpGitHubClient`.
- [x] **Step 4: Реализовать `HttpGitHubClient`, `GitHubLogin`, эндпоинты и провайдеры.** `state = secrets.token_urlsafe(16)`, сравнение через `secrets.compare_digest`.
- [x] **Step 5: Запустить тесты и линтеры.** Запуск: `make test-api && make lint-api`. Ожидается: всё зелёное.
- [x] **Step 6: Commit**

```bash
git add apps/api docs/superpowers/plans/2026-10-18-devplus-core.md
git commit -m "feat(api): GitHub OAuth login with state check and allowlist"
```

---

### Task 4: модуль progress и границы модулей

**Files:**
- Create: `apps/api/app/modules/progress/{__init__,models,service,schemas,router,providers}.py`
- Modify: `apps/api/app/core/container.py`, `apps/api/app/factory.py`, `apps/api/pyproject.toml` (import-linter), `Makefile` (`lint-api` += `uv run lint-imports`)
- Test: `apps/api/tests/test_progress.py`

**Interfaces:**
- Consumes: `CurrentUser` из `app.modules.auth.service`. Это единственный импорт из `auth`.
- Produces:
  - `LessonProgress` (таблица `lesson_progress`): `user_id` FK `"users.id"` `ON DELETE CASCADE`, `lesson_slug: str`, `completed_at` (server default `now()`), PK `(user_id, lesson_slug)`.
  - `@dataclass(frozen=True) CompletedLesson(lesson_slug: str, completed_at: datetime)`.
  - `ProgressService(session: AsyncSession)`:
    - `list_completed(user_id: UUID) -> list[CompletedLesson]`, сортировка по `completed_at`;
    - `mark_done(user_id: UUID, lesson_slug: str) -> None` через `insert … on_conflict_do_nothing`;
    - `unmark(user_id: UUID, lesson_slug: str) -> None`.
  - Эндпоинты:
    - `GET /api/progress` → `ProgressOut{completed: [{lesson_slug, completed_at}]}`;
    - `PUT` и `DELETE /api/progress/{module}/{lesson}` → 204.
    - У каждой части пути `Path(pattern=r"^[a-z0-9-]+$")`. Если общий slug длиннее 200 символов: `BadRequest("Lesson slug too long")`.
  - import-linter, два контракта типа `forbidden`:
    - `app.modules.progress` не импортирует `app.modules.auth.{models,router,github,providers}`;
    - `app.modules.auth` не импортирует `app.modules.progress`.

- [x] **Step 1: Написать падающие тесты в `tests/test_progress.py`.**

```python
async def test_progress_requires_session(client):
    assert (await client.get("/api/progress")).status_code == 401
    assert (await client.put("/api/progress/internet/dns")).status_code == 401

async def test_mark_and_unmark_are_idempotent(client, sign_in):
    await sign_in()
    for _ in range(2):
        assert (await client.put("/api/progress/internet/dns")).status_code == 204
    assert [c["lesson_slug"] for c in (await client.get("/api/progress")).json()["completed"]] == ["internet/dns"]
    for _ in range(2):
        assert (await client.delete("/api/progress/internet/dns")).status_code == 204
    assert (await client.get("/api/progress")).json() == {"completed": []}

@pytest.mark.parametrize("path", ["Internet/dns", "internet/dn_s", "internet/d%20ns"])
async def test_bad_slug_is_422(client, sign_in, path):
    await sign_in()
    assert (await client.put(f"/api/progress/{path}")).status_code == 422

async def test_slug_longer_than_200_is_400(client, sign_in):
    await sign_in()
    r = await client.put(f"/api/progress/{'a' * 100}/{'b' * 100}")  # 201 chars with the slash
    assert r.status_code == 400
    assert r.json() == {"detail": "Lesson slug too long"}

async def test_progress_is_per_user(client, sign_in):
    await sign_in("alice")
    await client.put("/api/progress/internet/dns")
    await sign_in("bob")
    assert (await client.get("/api/progress")).json() == {"completed": []}
```

- [x] **Step 2: Запустить тесты, убедиться, что они падают.** Запуск: `make test-api`. Ожидается: 404 на `/api/progress`.
- [x] **Step 3: Реализовать модуль `progress`.** Рядом с проверкой slug в `router.py` комментарий: `# shortcut: renaming a lesson orphans its progress; add a lesson manifest if renames become common`.
- [x] **Step 4: Запустить тесты, линтеры и проверку границ.** Запуск: `make test-api && make lint-api`. Ожидается: тесты зелёные, `lint-imports` выводит `Contracts: 2 kept, 0 broken.`
- [x] **Step 5: Проверить, что контракт ловит нарушение.** Временно добавить `from app.modules.auth.models import User` в `progress/service.py` и запустить `uv run lint-imports`. Ожидается: `1 broken`. Импорт удалить.
- [x] **Step 6: Commit**

```bash
git add apps/api Makefile docs/superpowers/plans/2026-10-18-devplus-core.md
git commit -m "feat(api): progress module with per-user lesson marks and module boundary contracts"
```

---

### Task 5: миграции Alembic

**Files:**
- Create: `apps/api/alembic.ini`, `apps/api/migrations/env.py`, `apps/api/migrations/script.py.mako`, `apps/api/migrations/versions/<rev>_initial.py`
- Modify: `Makefile` (цели `migrate` и `migrate-check`)

**Interfaces:**
- Consumes: `Base.metadata`, модели `auth` и `progress`, `Settings().database_url`.
- Produces: `make migrate` (`alembic upgrade head`), `make migrate-check` (`alembic check`).

- [x] **Step 1: Инициализировать Alembic.** `cd apps/api && uv run alembic init -t async migrations`. В `env.py`:
  - `url` берётся из `Settings().database_url`;
  - `target_metadata = Base.metadata`;
  - импортировать `app.modules.auth.models` и `app.modules.progress.models`.
- [x] **Step 2: Сгенерировать первую миграцию.** `uv run alembic revision --autogenerate -m "initial"` на пустой базе `devplus`. Прочитать файл миграции. В нём должны быть три таблицы с PK, FK `ON DELETE CASCADE`, unique на `github_id` и server defaults `now()`.
- [x] **Step 3: Проверить.** Запуск: `make migrate && make migrate-check`. Ожидается: `Running upgrade -> <rev>, initial` и `No new upgrade operations detected.`
- [x] **Step 4: Commit**

```bash
git add apps/api/alembic.ini apps/api/migrations Makefile docs/superpowers/plans/2026-10-18-devplus-core.md
git commit -m "feat(api): alembic migrations with initial schema"
```

---

### Task 6: каркас web, pnpm workspace и сгенерированный API-клиент

**Files:**
- Create: `package.json` (`{"private": true, "packageManager": "pnpm@10.13.1"}`), `pnpm-workspace.yaml` (`apps/web`, `packages/*`)
- Create: `apps/web/**` (create-next-app), `packages/api-client/{package.json,openapi.json,src/schema.d.ts,src/index.ts}`
- Create: `apps/web/lib/api.ts`, `apps/web/lib/browser-api.ts`, `apps/web/vitest.config.ts`
- Modify: `Makefile` (`web`, `dev`, `test-web`, `lint-web`, `gen-client`, агрегаты `test` и `lint`)

**Interfaces:**
- Produces:
  - `@devplus/api-client`: `createApiClient(baseUrl: string, headers?: HeadersInit)` = `createClient<paths>({ baseUrl, headers })`. Плюс реэкспорт `paths` и `components`.
  - `apps/web/lib/api.ts`: `serverApi(): Promise<ReturnType<typeof createApiClient>>`. Base URL берётся из `API_INTERNAL_URL`, заголовок `cookie` из `(await cookies()).toString()`.
  - `apps/web/lib/browser-api.ts`: `browserApi = createApiClient("")`, относительные запросы на тот же origin.
  - `make gen-client`:
    - `cd apps/api && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > ../../packages/api-client/openapi.json`;
    - затем `pnpm --filter @devplus/api-client exec openapi-typescript openapi.json -o src/schema.d.ts`.

- [x] **Step 1: Создать приложение.** `pnpm create next-app@16.4.2 apps/web --ts --tailwind --eslint --app --no-src-dir --import-alias "@/*" --use-pnpm --disable-git`. Если флаг не принимается, ответить на вопрос мастера тем же выбором.
  - Добавить: `pnpm --filter web add next-mdx-remote gray-matter @devplus/api-client@workspace:*` и `pnpm --filter web add -D vitest @mdx-js/mdx @tailwindcss/typography @playwright/test prettier`.
  - `.prettierrc` пустой `{}`. Скрипт `format:check`: `prettier --check .`. `.prettierignore` закрывает `.next`, `node_modules` и `content`.
  - `pnpm --filter web dlx shadcn@latest init`, затем `shadcn add button`.
  - `packages/api-client/package.json`: `{"name": "@devplus/api-client", "private": true, "type": "module", "main": "src/index.ts", "types": "src/index.ts", "dependencies": {"openapi-fetch": "0.17.0"}, "devDependencies": {"openapi-typescript": "7.13.0"}}`.
- [x] **Step 2: `next.config.ts`.**
  - `output: "standalone"`;
  - `outputFileTracingRoot` — корень репозитория;
  - `transpilePackages: ["@devplus/api-client"]`, потому что пакет поставляется исходниками TS;
  - `images.remotePatterns` для `avatars.githubusercontent.com`;
  - `rewrites()`: только при `NODE_ENV === "development"` правило `/api/:path*` → `${API_INTERNAL_URL}/api/:path*`.
- [x] **Step 3: Пакет `api-client` и цель `gen-client`.** Проверка: `make gen-client && grep -c '"/api/me"' packages/api-client/src/schema.d.ts`. Ожидается: `1`.
- [x] **Step 4: Цели Makefile.**
  - `web`: `pnpm --filter web dev`;
  - `dev`: `db`, затем `$(MAKE) -j2 api web`;
  - `test-web`: `pnpm --filter web exec vitest run`;
  - `lint-web`: `pnpm --filter web lint && pnpm --filter web format:check && pnpm --filter web exec next typegen && pnpm --filter web exec tsc --noEmit`.
    - Отклонение от брифа: `next typegen` нужен, потому что глобальные типы (`LayoutProps`, `PageProps`) генерирует Next, и на чистом чекауте `tsc` без него падает.
  - Агрегаты `test` и `lint` теперь включают web-цели.
  - Проверка: `make lint-web && pnpm --filter web build`. Ожидается: без ошибок.
- [x] **Step 5: Commit**

```bash
git add package.json pnpm-workspace.yaml pnpm-lock.yaml apps/web packages/api-client Makefile docs/superpowers/plans/2026-10-18-devplus-core.md
git commit -m "feat(web): Next.js app, pnpm workspace and generated API client"
```

---

### Task 7: загрузчик уроков, счётчики прогресса, пример урока

**Files:**
- Create: `apps/web/lib/content.ts`, `apps/web/lib/progress.ts`
- Create: `content/00-start/_module.json`, `content/00-start/01-how-to-use.mdx`
- Test: `apps/web/test/content.test.ts`, `apps/web/test/content-compile.test.ts`, `apps/web/test/fixtures/content/**`, `apps/web/test/fixtures/broken/**`

**Interfaces:**
- Produces:
  - `content.ts`:
    - `type LessonMeta = { slug: string; moduleSlug: string; lessonSlug: string; title: string; summary: string }`, где `slug = "module/lesson"`;
    - `type Module = { slug: string; title: string; description: string; lessons: LessonMeta[] }`;
    - `type Lesson = LessonMeta & { source: string }`, `source` — тело MDX без frontmatter;
    - `CONTENT_DIR = process.env.CONTENT_DIR ?? path.resolve(process.cwd(), "../../content")`;
    - `loadCurriculum(dir = CONTENT_DIR): Promise<Module[]>`;
    - `loadLesson(moduleSlug: string, lessonSlug: string, dir = CONTENT_DIR): Promise<Lesson | null>`.
    - Имена папок модулей подходят под `^\d{2}-([a-z0-9-]+)$`, файлов уроков под `^\d{2}-([a-z0-9-]+)\.mdx$`. Порядок задаёт префикс. Всё остальное игнорируется.
    - Ошибки: `Error("<path>: missing _module.json")` и `Error("<path>: frontmatter needs title and summary")`.
  - `progress.ts`: `moduleProgress(module: Module, done: ReadonlySet<string>): { done: number; total: number }`. Считаются только уроки самого модуля.

- [x] **Step 1: Фикстуры.**
  - `fixtures/content/`:
    - `00-start/_module.json` `{"title":"Старт","description":"d"}`, `00-start/01-hello.mdx`;
    - `01-internet/_module.json` `{"title":"Интернет","description":"Как работает сеть"}`, `01-internet/01-dns.mdx` (`title: DNS`, `summary: s`), `01-internet/02-tcp.mdx` (`title: TCP`), `01-internet/notes.txt`.
  - `fixtures/broken/`: `00-x/_module.json` и `00-x/01-no-title.mdx` (во frontmatter только `summary`).
  - `fixtures/no-module/`: `00-y/01-a.mdx` без `_module.json`.
- [x] **Step 2: Написать падающие тесты в `test/content.test.ts`.**

```ts
const FIX = path.join(__dirname, "fixtures/content");

test("orders modules and lessons by prefix and strips it", async () => {
  const mods = await loadCurriculum(FIX);
  expect(mods.map((m) => m.slug)).toEqual(["start", "internet"]);
  expect(mods[1].lessons.map((l) => [l.slug, l.title])).toEqual([["internet/dns", "DNS"], ["internet/tcp", "TCP"]]);
});

test("ignores files that are not lessons", async () => {
  const mods = await loadCurriculum(FIX);
  expect(mods[1].lessons).toHaveLength(2);
});

test("names the file when frontmatter is incomplete", async () => {
  await expect(loadCurriculum(path.join(__dirname, "fixtures/broken"))).rejects.toThrow(/01-no-title\.mdx: frontmatter needs title and summary/);
});

test("names the module dir when _module.json is missing", async () => {
  await expect(loadCurriculum(path.join(__dirname, "fixtures/no-module"))).rejects.toThrow(/00-y: missing _module\.json/);
});

test("loadLesson returns body without frontmatter, null when missing", async () => {
  const lesson = await loadLesson("internet", "dns", FIX);
  expect(lesson?.source).not.toContain("title:");
  expect(await loadLesson("internet", "nope", FIX)).toBeNull();
});

test("moduleProgress ignores marks for lessons that no longer exist", async () => {
  const [, internet] = await loadCurriculum(FIX);
  expect(moduleProgress(internet, new Set(["internet/dns", "gone/old"]))).toEqual({ done: 1, total: 2 });
});
```

- [x] **Step 3: Написать `test/content-compile.test.ts`.** Для каждого урока из реального `CONTENT_DIR` вызвать `compile(lesson.source)` из `@mdx-js/mdx`, ошибки быть не должно.
  - Отклонение от спеки: в спеке сломанный MDX ловит `next build`. Но страницы рендерятся динамически, потому что зависят от cookie сессии. Поэтому `next build` не компилирует MDX, и эту роль берёт на себя данный тест в CI.
- [x] **Step 4: Запустить тесты, убедиться, что они падают.** Запуск: `make test-web`. Ожидается: модули `lib/content` и `lib/progress` не найдены.
- [x] **Step 5: Реализовать `content.ts` и `progress.ts`. Написать урок `content/00-start/01-how-to-use.mdx`** «Как пользоваться devplus»:
  - frontmatter `title` и `summary`;
  - шесть разделов шаблона из раздела 4 спеки: «Зачем это знать», «Теория», «Как спрашивают на интервью», «Самопроверка» с `<details>`, «Практика», «Что почитать дальше»;
  - текст про то, как устроены модули, отметки и программа.
  - `_module.json`: `{"title":"Старт","description":"Как устроена платформа"}`.
- [x] **Step 6: Запустить тесты и линтеры.** Запуск: `make test-web && make lint-web`. Ожидается: всё зелёное.
- [x] **Step 7: Commit**

```bash
git add apps/web content docs/superpowers/plans/2026-10-18-devplus-core.md
git commit -m "feat(web): lesson loader, progress counts, first lesson"
```

---

### Task 8: страницы и e2e smoke-тест

**Files:**
- Create: `apps/web/lib/session.ts`, `apps/web/components/{header,logout-button,progress-toggle}.tsx`
- Create: `apps/web/app/(app)/layout.tsx`, `apps/web/app/(app)/page.tsx`, `apps/web/app/(app)/lessons/[module]/[lesson]/page.tsx`, `apps/web/app/no-access/page.tsx`
- Delete: стартовая `apps/web/app/page.tsx` от create-next-app
- Create: `apps/api/scripts/seed_e2e.py`, `apps/web/playwright.config.ts`, `apps/web/e2e/global-setup.ts`, `apps/web/e2e/smoke.spec.ts`
- Modify: `Makefile` (цель `e2e`: `pnpm --filter web exec playwright test`)

**Interfaces:**
- Consumes: `serverApi`, `browserApi` (Task 6), `loadCurriculum`, `loadLesson`, `moduleProgress` (Task 7), API из Task 2–4.
- Produces:
  - `session.ts`: `requireUser(): Promise<components["schemas"]["MeOut"]>`. На 401 делает `redirect("/api/auth/github/login")`, на 403 `redirect("/no-access")`, на другую ошибку бросает исключение.
  - `ProgressToggle({ slug, done }: { slug: string; done: boolean })`, клиентский компонент. Отправляет `PUT` или `DELETE /api/progress/{module}/{lesson}` через `browserApi`, затем вызывает `router.refresh()`.
  - `LogoutButton`, клиентский компонент. Отправляет `POST /api/auth/logout`, затем `window.location.assign("/no-access?signed_out=1")`.
  - `seed_e2e.py`, запускается через `uv run python scripts/seed_e2e.py`:
    - upsert пользователя `github_id=-1`, `login="e2e-user"`, `name="E2E"`;
    - удаляет его прогресс;
    - создаёт сессию;
    - печатает сырой токен в stdout.
    - Работает с моделями `auth` и `progress` и `hash_token` напрямую. Это скрипт, а не модуль, поэтому контракты на него не распространяются.

**Тексты интерфейса (точные):**
- Шапка: `devplus`, аватар и кнопка `Выйти`.
- Главная:
  - заголовок `Программа`;
  - у модуля счётчик `{done} из {total}`;
  - уроки списком, пройденные отмечены `✓`.
- Урок:
  - `<h1>` с заголовком урока;
  - тело в `prose` (Tailwind typography);
  - кнопка `Отметить пройденным` или `Снять отметку`;
  - ссылка `← К программе`.
- `/no-access`:
  - заголовок `Нет доступа`, текст `Попроси добавить твой GitHub-логин в список доступа devplus.`;
  - при `?signed_out=1` заголовок `Ты вышел из devplus` без второй строки;
  - в обоих вариантах ссылка `Войти через GitHub` на `/api/auth/github/login`.
  - Отклонение от спеки: вариант после выхода добавлен на ту же страницу, отдельный маршрут не заводим.

- [x] **Step 1: Настроить Playwright.**
  - `playwright.config.ts`, `webServer` из двух процессов:
    - api: `cd ../api && uv run uvicorn app.main:app --port 8000`, URL готовности `http://localhost:8000/api/health`, env `ALLOWED_GITHUB_LOGINS=e2e-user`, `APP_ORIGIN=http://localhost:3000`, `COOKIE_SECURE=false`, `GITHUB_CLIENT_ID=e2e`, `GITHUB_CLIENT_SECRET=e2e`, `DATABASE_URL` из окружения;
    - web: `pnpm dev`, URL готовности `http://localhost:3000/no-access`, env `API_INTERNAL_URL=http://localhost:8000`.
  - `use.baseURL = "http://localhost:3000"`.
  - `global-setup.ts`: `execSync("uv run python scripts/seed_e2e.py", { cwd: "../api" })`, токен кладётся в `process.env.E2E_SESSION_TOKEN`.
- [x] **Step 2: Написать падающий e2e-тест `e2e/smoke.spec.ts`.**

```ts
test("signed-in user opens a lesson and marks it done", async ({ page, context }) => {
  await context.addCookies([{ name: "session", value: process.env.E2E_SESSION_TOKEN!, domain: "localhost", path: "/" }]);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Программа" })).toBeVisible();
  await expect(page.getByText("0 из 1")).toBeVisible();
  await page.getByRole("link", { name: "Как пользоваться devplus" }).click();
  await page.getByRole("button", { name: "Отметить пройденным" }).click();
  await expect(page.getByRole("button", { name: "Снять отметку" })).toBeVisible();
  await page.getByRole("link", { name: "← К программе" }).click();
  await expect(page.getByText("1 из 1")).toBeVisible();
});

test("anonymous visitor is sent to GitHub login", async ({ page }) => {
  const res = await page.request.get("/", { maxRedirects: 0 });
  expect(res.status()).toBe(307);
  expect(res.headers()["location"]).toContain("/api/auth/github/login");
});

test("no-access page offers GitHub login", async ({ page }) => {
  await page.goto("/no-access");
  await expect(page.getByRole("heading", { name: "Нет доступа" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Войти через GitHub" })).toHaveAttribute("href", "/api/auth/github/login");
});
```

- [x] **Step 3: Запустить тест, убедиться, что он падает.** Запуск: `make db && make migrate && pnpm --filter web exec playwright install chromium && make e2e`. Ожидается: FAIL, нет заголовка «Программа».
- [x] **Step 4: Реализовать `session.ts`, компоненты и страницы.**
  - `(app)/layout.tsx` вызывает `requireUser()` и рисует `Header`.
  - Главная и урок запрашивают `/api/progress` через `serverApi()`.
  - Для неизвестного урока вызывается `notFound()`.
  - Урок рендерится через `MDXRemote` из `next-mdx-remote/rsc`.
- [x] **Step 5: Запустить e2e и линтеры.** Запуск: `make e2e && make lint-web && make test-web`. Ожидается: 3 passed, остальное зелёное.
- [x] **Step 6: Commit**

```bash
git add apps/web apps/api/scripts Makefile docs/superpowers/plans/2026-10-18-devplus-core.md
git commit -m "feat(web): curriculum, lesson and no-access pages with progress toggle; e2e smoke"
```

---

### Task 9: Docker-образы, продовый compose и Caddy

**Files:**
- Create: `apps/api/Dockerfile`, `apps/api/.dockerignore`, `apps/web/Dockerfile`, `.dockerignore` (корень, для контекста web)
- Create: `infra/docker-compose.yml`, `infra/Caddyfile`, `infra/app.env.example`

**Interfaces:**
- Produces:
  - Образы `ghcr.io/hhaakkimm/devplus-api:${IMAGE_TAG}` (контекст `apps/api`) и `ghcr.io/hhaakkimm/devplus-web:${IMAGE_TAG}` (контекст корень репозитория, файл `apps/web/Dockerfile`).
  - Сервисы compose:
    - `postgres`: `postgres:17`, `environment: POSTGRES_USER=devplus, POSTGRES_DB=devplus`, пароль из `app.env`, том `pgdata`, healthcheck;
    - `migrate`: образ api, команда `alembic upgrade head`, `depends_on: postgres: service_healthy`;
    - `api`: `depends_on: migrate: service_completed_successfully`;
    - `web`: `API_INTERNAL_URL=http://api:8000`, `CONTENT_DIR=/app/content`;
    - `caddy`: `caddy:2`, порты 80 и 443, тома `Caddyfile` и `caddy_data`.
    - Все сервисы с `env_file: app.env`.
  - `app.env.example`: `DOMAIN`, `POSTGRES_PASSWORD`, `DATABASE_URL=postgresql+asyncpg://devplus:${POSTGRES_PASSWORD}@postgres:5432/devplus` (развернуть вручную), `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `ALLOWED_GITHUB_LOGINS`, `APP_ORIGIN=https://<DOMAIN>`, `COOKIE_SECURE=true`.

- [x] **Step 1: Dockerfile.**
  - **api:** `python:3.13-slim`, `COPY --from=ghcr.io/astral-sh/uv:0.9.21 /uv /bin/uv`, `uv sync --frozen --no-dev`, `CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]`.
  - **web:** `node:24-alpine`, multi-stage. Включить `corepack` и pnpm, `pnpm install --frozen-lockfile`, `pnpm --filter web build`. В runner скопировать `apps/web/.next/standalone`, `.next/static`, `public` и `content/` в `/app/content`. Запуск `node apps/web/server.js`.
- [x] **Step 2: `infra/Caddyfile`.** Значения заголовков взяты из спеки:

```
{$DOMAIN} {
	encode zstd gzip
	header {
		Strict-Transport-Security "max-age=31536000; includeSubDomains"
		X-Content-Type-Options "nosniff"
		Referrer-Policy "strict-origin-when-cross-origin"
		-Server
	}
	handle /api/* {
		reverse_proxy api:8000
	}
	handle {
		reverse_proxy web:3000
	}
}
```

- [x] **Step 3: Локальная проверка всего стека.**
  - Собрать образы с тегом `local`.
  - Добавить `infra/app.env` в `.gitignore`: правило `.env` его не покрывает.
  - Создать `infra/app.env` из примера с `DOMAIN=localhost`, `APP_ORIGIN=https://localhost`.
  - `cd infra && IMAGE_TAG=local docker compose up -d --wait`.
  - Проверка:
    - `curl -sk https://localhost/api/health` → `{"status":"ok"}`;
    - `curl -sk -o /dev/null -w '%{http_code} %{redirect_url}' https://localhost/` → `307 https://localhost/api/auth/github/login`;
    - `curl -skI https://localhost/api/health | grep -i strict-transport` даёт непустой результат.
  - После проверки: `docker compose down`.
- [x] **Step 4: Commit**

```bash
git add apps/api/Dockerfile apps/api/.dockerignore apps/web/Dockerfile .dockerignore infra .gitignore docs/superpowers/plans/2026-10-18-devplus-core.md
git commit -m "feat(infra): docker images, production compose and Caddy"
```

---

### Task 10: CI и Dependabot

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/dependabot.yml`

**Interfaces:**
- Produces: workflow `CI` (`name: CI`) на `pull_request` и `push` в `main`. На его успех опирается Task 11.

- [x] **Step 1: `ci.yml`, три job.**
  - **`api`:**
    - service `postgres:17` с `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` = `devplus`, плюс `psql -c 'CREATE DATABASE devplus_test'`;
    - `astral-sh/setup-uv`, `uv sync`;
    - `make lint-api`;
    - `DATABASE_URL=…/devplus make migrate migrate-check`;
    - `make test-api`.
  - **`web`:** `pnpm/action-setup`, `actions/setup-node` (24, кэш pnpm), `pnpm install --frozen-lockfile`, `make lint-web test-web`, `pnpm --filter web build`.
  - **`e2e`:**
    - Postgres как в job `api`, uv и pnpm, `make migrate`;
    - `make gen-client && git diff --exit-code packages/api-client` с фиктивными `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `APP_ORIGIN`;
    - `pnpm --filter web exec playwright install --with-deps chromium`, `make e2e`.
- [x] **Step 2: `dependabot.yml`.** Экосистемы `uv` (`/apps/api`), `npm` (`/`) и `github-actions` (`/`), все `weekly`.
- [ ] **Step 3: Проверить.**
  - Запушить ветку `ci-setup` и открыть PR.
  - Ожидается: три job зелёные, Dependabot виден в Insights → Dependency graph.
  - Если job падает из-за окружения CI, чинить workflow, а не тесты.
- [x] **Step 4: Commit**

```bash
git add .github docs/superpowers/plans/2026-10-18-devplus-core.md
git commit -m "ci: lint, tests, migrations check, client freshness and e2e; dependabot"
```

---

### Task 11: CD на VPS, документация деплоя и итог

**Files:**
- Create: `.github/workflows/deploy.yml`, `docs/deploy.md`
- Modify: `CLAUDE.md` (снять пометку «команды появятся с ядром»), `docs/roadmap.html` (ядро реализовано, следующий — оценщик), `README.md` (ссылка на `docs/deploy.md`)

**Interfaces:**
- Consumes: workflow `CI` (Task 10), образы и compose (Task 9).
- Produces:
  - Деплой на `workflow_run` workflow `CI` (`types: [completed]`, `branches: [main]`, `if: conclusion == 'success'`).
  - Секреты репозитория: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.
  - Раскладка на сервере: `/opt/devplus/{docker-compose.yml, Caddyfile, app.env, .env}`. В `.env` только `IMAGE_TAG=<sha>`, его пишет деплой.

- [ ] **Step 1: `deploy.yml`.**
  - `permissions: packages: write`;
  - `actions/checkout` с `ref: ${{ github.event.workflow_run.head_sha }}`;
  - `docker/login-action` в GHCR;
  - `docker/build-push-action` для двух образов с тегом `${{ github.event.workflow_run.head_sha }}`;
  - `scp` для `infra/docker-compose.yml` и `infra/Caddyfile` в `/opt/devplus/`;
  - `ssh … "cd /opt/devplus && echo IMAGE_TAG=<sha> > .env && docker compose pull && docker compose up -d --wait"`.
  - SSH-ключ из секрета записывается во временный файл, `StrictHostKeyChecking=accept-new`.
- [ ] **Step 2: `docs/deploy.md`.**
  - Подготовка VPS: Docker, `docker login ghcr.io` с PAT `read:packages`, `/opt/devplus/app.env` из `infra/app.env.example`, DNS A-запись на VPS.
  - Продовое OAuth-приложение GitHub: callback `https://<DOMAIN>/api/auth/github/callback`.
  - Секреты репозитория.
  - Откат: `echo IMAGE_TAG=<old-sha> > .env && docker compose up -d --wait`.
  - Добавление человека: правка `ALLOWED_GITHUB_LOGINS` в `app.env` и `docker compose up -d api`.
- [ ] **Step 3: Проверить.**
  - Локально: `cd infra && IMAGE_TAG=x docker compose config >/dev/null`. Ожидается: без ошибок.
  - Полная проверка возможна только на настоящем VPS после настройки по `docs/deploy.md`: пуш в `main` → зелёный CI → зелёный Deploy → `curl https://<DOMAIN>/api/health`. Если VPS ещё не готов, честно записать в отчёт, что этот шаг не проверен.
- [ ] **Step 4: Итог.**
  - В `CLAUDE.md` убрать «Код ещё не написан» и «(появятся с ядром)».
  - В `docs/roadmap.html` у подпроекта 1 все шаги `done` и pill `готово`, у подпроекта 2 pill `now` и «проектируется», в строке этапа «ядро готово, следующий — оценщик промптов». Перепубликовать артефакт.
- [ ] **Step 5: Commit**

```bash
git add .github/workflows/deploy.yml docs/deploy.md CLAUDE.md docs/roadmap.html README.md docs/superpowers/plans/2026-10-18-devplus-core.md
git commit -m "ci: deploy to VPS via GHCR; docs and roadmap for completed core"
```
