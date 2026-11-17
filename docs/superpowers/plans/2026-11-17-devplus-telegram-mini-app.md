# Telegram Mini App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Команда открывает devplus из Telegram-бота одним тапом; Telegram-аккаунт один раз привязывается к существующему GitHub-пользователю с подтверждением.

**Architecture:** В модуль `auth` добавляются проверка `initData`, вход по `telegram_id` и привязка через GitHub OAuth в системном браузере с обязательной страницей подтверждения. В `apps/web` добавляются страницы `/tg*` вне авторизованных layout-групп и cookie `miniapp=1`, по которой 401 ведёт на `/tg`, а не на GitHub-вход внутри WebView.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, dishka, pytest; Next.js App Router, vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-17-devplus-telegram-mini-app-design.md`

## Global Constraints

- Токен привязки одноразовый, хранится хэшем (`hash_token`), живёт 10 минут; `auth_date` не старше 1 часа.
- Сравнение хэшей только через `secrets.compare_digest` в байтах.
- `TELEGRAM_BOT_TOKEN` необязателен (по умолчанию `""`); пока пуст, все пять `/api/auth/telegram*` отвечают `404`.
- Ошибки API: `{"detail": "..."}`, доменные исключения из `app.core.errors`. Остальные модули API не затрагиваются (import-linter).
- Cookie сессии те же параметры, что после GitHub (`SESSION_COOKIE`, `SESSION_TTL`, `httponly`, `samesite="lax"`, `secure=settings.cookie_secure`, `path="/"`).
- Telegram Web (фрейм) не поддерживаем: `shortcut:` комментарий рядом с установкой cookie.
- После изменения API: `make gen-client` и коммит клиента. Миграцию читать глазами перед коммитом.
- Отвязки из интерфейса и серверной «Отмены» нет.

## Review Focus

- `initData` с полем `signature` и кириллическим `first_name` проходит проверку (в `data_check_string` входят все поля кроме `hash`). Тест в Task 1.
- Повтор `confirm` и вызов `pending`/`confirm` без cookie `tg_link` не привязывают ничего. Тест в Task 3.
- `telegram_id`, уже занятый другим пользователем, даёт 400 и не оставляет частичной привязки; гонка двух `confirm` не даёт 500. Тест в Task 3.
- Привязанный пользователь, убранный из allowlist, получает 403, а не сессию. Тест в Task 2.
- Cookie `miniapp=1` осталась в обычном браузере: `/tg` без `initData` стирает её и предлагает обычный вход, а не тупик. Тест в Task 5.

---

### Task 1: Данные, конфиг и проверка `initData`

**Files:**
- Modify: `apps/api/app/core/config.py`, `apps/api/app/modules/auth/models.py`, `.env.example`, `infra/app.env.example`
- Create: `apps/api/app/modules/auth/telegram.py`, `apps/api/migrations/versions/<rev>_telegram.py` (autogenerate)
- Modify: `apps/api/tests/conftest.py` (helper `sign_init_data`)
- Test: `apps/api/tests/test_telegram_init_data.py`

**Interfaces:**
- Produces: `Settings.telegram_bot_token: str = ""`; `User.telegram_id: Mapped[int | None]` (`BigInteger`, unique); `TelegramLinkRequest` (`token_hash` PK `str`, `telegram_id` `BigInteger`, `first_name` `str`, `username` `str | None`, `user_id` `UUID | None` FK `users.id` `ondelete="CASCADE"`, `expires_at` tz-aware).
- Produces: `@dataclass(frozen=True) TelegramUser(id: int, first_name: str, username: str | None)`; `verify_init_data(init_data: str, bot_token: str, now: datetime, max_age: timedelta = timedelta(hours=1)) -> TelegramUser`, бросает `Unauthorized("Invalid Telegram data")`.
- Produces (conftest): `sign_init_data(bot_token: str, user: dict, auth_date: int, **extra: str) -> str` возвращает URL-кодированную строку с корректным `hash`; поля `user` (JSON-строка), `auth_date`, `extra`.

- [x] **Step 1: Write failing tests** в `test_telegram_init_data.py`: `test_valid_init_data_returns_user` (id, first_name, username); `test_user_with_signature_and_cyrillic_name` (`extra={"signature": "abc"}`, `first_name="Иван"`, проходит); `test_tampered_hash_rejected`; `test_tampered_field_rejected` (после подписи меняется `user`); `test_missing_hash_rejected`; `test_stale_auth_date_rejected` (старше 1 часа); `test_fresh_auth_date_accepted` (59 минут); `test_non_ascii_hash_does_not_crash` (`hash=é`, ждём `Unauthorized`, не `TypeError`); `test_malformed_user_json_rejected`; `test_wrong_bot_token_rejected`.
- [x] **Step 2: Run** `cd apps/api && uv run pytest tests/test_telegram_init_data.py -v`. Expected: FAIL (module missing).
- [x] **Step 3: Implement** `telegram.py`: `secret = hmac.new(b"WebAppData", bot_token.encode(), sha256).digest()`; `data_check_string` из пар `parse_qsl(init_data, keep_blank_values=True)` без `hash`, отсортированных по ключу, `k=v` через `\n`; hash ожидаемый `hmac.new(secret, dcs.encode(), sha256).hexdigest()`; сравнение `compare_digest(expected.encode(), received.encode())`; `user` через `json.loads`, любые ошибки разбора дают `Unauthorized`.
- [x] **Step 4: Add** `telegram_bot_token: str = ""` в `Settings`; поле `telegram_id` и модель `TelegramLinkRequest` в `models.py`; `TELEGRAM_BOT_TOKEN=` в `.env.example` и `infra/app.env.example` (комментарий: пусто отключает вход через Telegram).
- [x] **Step 5: Migration:** `cd apps/api && uv run alembic revision --autogenerate -m "telegram"`, прочитать файл (ожидаются: колонка и unique-констрейнт на `users.telegram_id`, таблица `telegram_link_requests`), `make migrate && make migrate-check`.
- [x] **Step 6: Run** `uv run pytest tests/test_telegram_init_data.py -v && make lint`. Expected: PASS.
- [x] **Step 7: Commit** `feat(auth): telegram_id, link requests table, initData verification`.

### Task 2: Вход по `initData`

**Files:**
- Modify: `apps/api/app/modules/auth/service.py`, `router.py`, `schemas.py`, `providers.py`
- Test: `apps/api/tests/test_auth_telegram.py`

**Interfaces:**
- Consumes: `verify_init_data`, `TelegramUser`, `sign_init_data` (Task 1).
- Produces: `class TelegramLogin(auth: AuthService, settings: Settings)` в `service.py` (регистрируется в `AuthProvider` через `provide(TelegramLogin)`): `require_configured() -> None` (`NotFound("Telegram login is not configured")` при пустом токене); `verify(init_data: str) -> TelegramUser` (вызывает `require_configured`, затем `verify_init_data(..., now=datetime.now(UTC))`); `async login(init_data: str) -> tuple[str, CurrentUser]` (токен сессии и пользователь; `NotFound("Telegram not linked")`, `Forbidden("Access revoked")` если логин вне allowlist).
- Produces: `AuthService.user_by_telegram_id(telegram_id: int) -> User | None`; `schemas.TelegramInitIn(init_data: str)`; `POST /api/auth/telegram` → `200 MeOut` + cookie `session`.
- Test fixture: в `test_auth_telegram.py` переопределить `settings` (`def settings(settings): return settings.model_copy(update={"telegram_bot_token": TOKEN})`).

- [x] **Step 1: Write failing tests:** `test_login_sets_session_for_linked_user` (после ответа `/api/me` вернёт логин); `test_bad_signature_401`; `test_stale_init_data_401`; `test_unlinked_telegram_404`; `test_linked_user_outside_allowlist_403` (в `users` login `mallory`, `telegram_id` задан, сессии нет); `test_unconfigured_token_404` (`settings` с пустым токеном; пока проверять только этот эндпоинт, остальные добавит Task 3).
- [x] **Step 2: Run** `uv run pytest tests/test_auth_telegram.py -v`. Expected: FAIL.
- [x] **Step 3: Implement** как в Interfaces. Router: повторить параметры cookie из `github_callback`; вынести установку session cookie в общую функцию `set_session_cookie(response, token, settings)` и вызвать из обоих мест.
- [x] **Step 4: Run** `uv run pytest tests/test_auth_telegram.py tests/test_auth_github.py tests/test_auth_sessions.py -v && make gen-client && make lint`. Expected: PASS, клиент обновился.
- [x] **Step 5: Commit** `feat(auth): POST /api/auth/telegram signs in a linked Telegram user`.

### Task 3: Привязка Telegram через GitHub с подтверждением

**Files:**
- Modify: `apps/api/app/modules/auth/service.py`, `router.py`, `schemas.py`
- Test: `apps/api/tests/test_auth_telegram_link.py`

**Interfaces:**
- Consumes: `TelegramLogin.verify`, `AuthService`, `hash_token`, `GitHubLogin`.
- Produces в `service.py`: константа `TG_LINK_COOKIE = "tg_link"`; `TelegramLogin.start_link(init_data: str) -> str` (удаляет просроченные заявки, создаёт строку `expires_at = now + 10 min`, возвращает `f"{app_origin}/api/auth/telegram/link?token=<token>"`); `TelegramLogin.open_link(token: str) -> None` (заявка есть, не просрочена, `user_id` пуст, иначе `BadRequest("invalid")`); `GitHubLogin.complete_link(code: str, token: str) -> str` (логин вне allowlist: удалить заявку и `BadRequest("not_allowed")`; иначе `upsert_user` и одним `UPDATE` (заявка жива, `user_id IS NULL`) записать `user_id` и заменить хэш токена на хэш нового секрета; вернуть секрет, иначе `BadRequest("invalid")`; токен из `link-start` знает создатель ссылки, поэтому он не должен подтверждать); `TelegramLogin.pending(token: str) -> LinkPending` (`dataclass`: `telegram_id`, `first_name`, `username`, `login`; `NotFound` если заявки нет, она просрочена или `user_id` пуст); `TelegramLogin.confirm(token: str, telegram_id: int) -> None` (по спеке п. 6: `DELETE … RETURNING` заявки с `user_id IS NOT NULL`, `NotFound` если строки нет; `telegram_id` не равен `telegram_id` заявки: `BadRequest("Telegram does not match the confirmation")`; занятый `telegram_id` и `IntegrityError` дают `BadRequest("Telegram is linked to another account")`; заявка удаляется в любом исходе).
- Produces эндпоинты: `POST /api/auth/telegram/link-start` (`{init_data}` → `{url}`); `GET /api/auth/telegram/link?token=` (cookie `tg_link`, `httponly`, `path="/api/auth"`, 10 минут, плюс state-cookie и редирект на GitHub, как в `github_login`); `GET /api/auth/telegram/link/pending` → `{telegram: {id, first_name, username}, login}`; `POST /api/auth/telegram/link/confirm` (тело `{telegram_id: int}`, схема `TelegramLinkConfirmIn`) → `204`, сбрасывает `tg_link`. Все начинаются с `require_configured`, то есть без токена бота `404` приходит до проверки тела, не `422`. `TelegramInitIn.init_data` ограничен `max_length=4096`.
- Изменение: `github_callback` при наличии cookie `tg_link` не создаёт сессию, вызывает `complete_link`, ставит cookie `tg_link` с возвращённым секретом (ротация, см. спеку) и редиректит на `/tg/confirm`; при любой `BadRequest` в этой ветке (в том числе неверный state) удаляет `tg_link` и state и редиректит на `/tg/link-failed?reason=<detail>`. `GET /api/auth/telegram/link` при `BadRequest` тоже редиректит на `link-failed`. Без `tg_link` поведение прежнее.

- [x] **Step 1: Write failing tests** (хелпер `link_through_github(client, token)`: `GET link?token=`, затем `GET /api/auth/github/callback?code=x&state=<oauth_state>`): `test_link_start_stores_name_and_returns_url`; `test_link_start_bad_signature_401`; `test_callback_with_tg_link_sets_user_id_but_not_telegram_id_and_no_session`; `test_pending_returns_telegram_name_and_login`; `test_confirm_links_and_deletes_request`; `test_no_confirm_no_link`; `test_confirm_twice_fails`; `test_confirm_without_tg_link_cookie_fails`; `test_expired_token_redirects_to_link_failed` (reason `invalid`); `test_login_outside_allowlist_redirects_to_link_failed_not_allowed_and_deletes_request`; `test_telegram_id_taken_by_other_user_400_on_confirm`; `test_relink_replaces_own_telegram_id`; `test_expired_requests_are_deleted_on_start`; `test_plain_github_login_unchanged_with_stray_request_row`; `test_unconfigured_token_404_on_all_five` (parametrize POST/GET по пяти путям).
- [x] **Step 2: Run** `uv run pytest tests/test_auth_telegram_link.py -v`. Expected: FAIL.
- [x] **Step 3: Implement** по Interfaces. Просрочку проверять в SQL (`expires_at > func.now()`), как у сессий.
- [x] **Step 4: Run** `uv run pytest tests/test_auth_telegram_link.py tests/test_auth_telegram.py tests/test_auth_github.py -v && make gen-client && make lint && make test`. Expected: PASS.
- [x] **Step 5: Commit** `feat(auth): link Telegram to a GitHub user with explicit confirmation`.

### Task 4: Сессия внутри Mini App (web)

**Files:**
- Create: `apps/web/lib/miniapp.ts`
- Modify: `apps/web/lib/session.ts`, `apps/web/lib/evals.ts`, `apps/web/lib/browser-api.ts`, `apps/web/components/app-shell.tsx`, `apps/web/components/header.tsx`, `apps/web/components/code-review/review-workspace.tsx`, `apps/web/components/lab/use-action.ts`, `apps/web/components/lab/run-status.tsx`
- Test: `apps/web/test/miniapp.test.ts`, `apps/web/e2e/miniapp.spec.ts`

**Interfaces:**
- Produces в `lib/miniapp.ts`: `MINIAPP_COOKIE = "miniapp"`; `signInUrl(cookieHeader: string): string` (`"/tg"`, если в заголовке есть `miniapp=1`, иначе `"/api/auth/github/login"`); `markMiniApp(): void` (ставит `document.cookie = "miniapp=1; path=/; max-age=2592000; SameSite=Lax"`, рядом `// shortcut: Telegram Web (фрейм) не поддерживаем, SameSite=lax cookie там может не сохраниться; менять, если команда пользуется Telegram Web`); `clearMiniApp(): void`.
- Changes: `redirectOnAuthError(status: number): Promise<void>` (async, 401 редиректит на `signInUrl((await cookies()).toString())`); все вызовы получают `await`. В `browser-api.ts` `SIGN_IN_URL` заменяется функцией `signInUrl(document.cookie)` в трёх клиентских местах. `Header` получает проп `showLogout: boolean`, `AppShell` передаёт `!miniApp` (из `cookies()`).

- [x] **Step 1: Write failing tests:** vitest `signInUrl` (пустой заголовок, с `miniapp=1`, с `miniapp=0`, с чужим cookie `xminiapp=1`); Playwright `miniapp.spec.ts`: без сессии, но с cookie `miniapp=1`, переход на `/` приводит на `/tg`; с сессией и `miniapp=1` кнопки «Выйти» нет; с сессией без `miniapp` кнопка есть.
- [x] **Step 2: Run** `cd apps/web && pnpm vitest run test/miniapp.test.ts`. Expected: FAIL.
- [x] **Step 3: Implement** по Interfaces; пройти `rtk grep` по `redirectOnAuthError` и `SIGN_IN_URL`, нигде не должно остаться неожиданного синхронного вызова (иначе eslint `no-floating-promises`/типы покажут).
- [x] **Step 4: Run** `pnpm vitest run && make lint && make e2e` (`miniapp.spec.ts` пока падает на `/tg` без страницы; допустимо до Task 5, зафиксировать).
- [x] **Step 5: Commit** `feat(web): Mini App session handling: 401 goes to /tg, logout hidden`.

### Task 5: Страницы `/tg`

**Files:**
- Create: `apps/web/lib/telegram.ts`, `apps/web/app/tg/page.tsx`, `apps/web/components/tg/telegram-login.tsx`, `apps/web/app/tg/confirm/page.tsx`, `apps/web/components/tg/link-confirm.tsx`, `apps/web/app/tg/linked/page.tsx`, `apps/web/app/tg/link-failed/page.tsx`
- Test: `apps/web/test/telegram.test.ts`, `apps/web/e2e/telegram.spec.ts`

**Interfaces:**
- Consumes: сгенерированный клиент (`/api/auth/telegram`, `link-start`, `link/pending`, `link/confirm`), `markMiniApp`, `clearMiniApp`.
- Produces в `lib/telegram.ts`: объявление `window.Telegram?.WebApp` (`initData`, `ready()`, `expand()`, `openLink(url)`, `onEvent("activated", cb)`); `nextStep(status: number): "home" | "link" | "no-access" | "open-telegram" | "error"` (200→home, 404→link, 403→no-access, 401→open-telegram, остальное→error); `linkFailedMessage(reason: string | undefined): string` (`invalid`: ссылка устарела или уже использована; `not_allowed`: твоего GitHub-логина нет в списке доступа; иначе общий текст).
- Page `/tg` (клиентский компонент, `telegram-web-app.js` грузится через `next/script`, без этого `initData` пуст): если `initData` пуст, вызвать `clearMiniApp()`, показать «Открой приложение из Telegram» и ссылку «Обычный вход» на `/api/auth/github/login`; иначе `markMiniApp()`, `ready()`, `expand()`, `POST /api/auth/telegram`, действие по `nextStep`. Для `link`: кнопка «Войти через GitHub» вызывает `link-start` и `openLink(url)`; повтор входа по `activated`, `visibilitychange` и кнопке «Я вошёл, продолжить».
- Page `/tg/confirm`: `pending`, показать «Привязать Telegram *first_name (@username, id N)* к аккаунту *login*?» с пояснением «Если ты не запрашивал привязку, закрой страницу»; кнопка «Привязать» вызывает `confirm` с телом `{telegram_id}` из единственного ответа `pending` (повторно `pending` не запрашивать) и переходит на `/tg/linked`; `400` и `404` от `confirm` блокируют кнопку и просят начать заново из Telegram, остальные ошибки показывать через `apiDetail`; рядом с именем `@username` или «без username» и строка «Убедись, что ты сам только что нажал «Войти через GitHub» в Telegram.».
- Pages `/tg/linked` («Готово, вернись в Telegram») и `/tg/link-failed` (текст из `linkFailedMessage(reason)`), статические.

- [x] **Step 1: Write failing tests:** vitest `nextStep` (все пять исходов) и `linkFailedMessage` (три ветки); Playwright `telegram.spec.ts`: `/tg` без Telegram показывает «Открой приложение из Telegram» и ссылку «Обычный вход», cookie `miniapp` после этого нет (в т.ч. если была до); `/tg/linked` и `/tg/link-failed?reason=invalid` отрисовывают тексты; `/tg/confirm` без `tg_link` показывает ошибку, а не падает.
- [x] **Step 2: Run** `pnpm vitest run test/telegram.test.ts`. Expected: FAIL.
- [x] **Step 3: Implement** по Interfaces; страницы лежат вне групп `(app)` и `(wide)`.
- [x] **Step 4: Run** `pnpm vitest run && make lint && make e2e` (включая `miniapp.spec.ts` из Task 4). Expected: PASS.
- [x] **Step 5: Commit** `feat(web): /tg Mini App pages: login, GitHub link, confirmation`.

### Task 6: Телефонный вид, деплой-инструкции, ручная проверка

**Files:**
- Modify: `docs/deploy.md`, при необходимости компоненты уроков и квизов (`apps/web/components/curriculum-nav.tsx`, `quiz.tsx`, `lesson-toc.tsx`, страницы уроков и квизов)
- Test: `apps/web/e2e/phone.spec.ts`

- [x] **Step 1: Write failing test** `phone.spec.ts` (viewport 390×844, сессия из `E2E_SESSION_TOKEN`): страница урока и страница квиза не имеют горизонтальной прокрутки (`document.documentElement.scrollWidth <= clientWidth`), «Отметить пройденным» и ответы квиза доступны.
- [x] **Step 2: Run** `make e2e`. Если тест уже зелёный, перейти к Step 4. Иначе исправить только то, что мешает читать урок или проходить квиз (спека: симулятор, code review, Лабораторию не адаптируем).
- [x] **Step 3: Run** `make e2e`. Expected: PASS.
- [x] **Step 4: docs/deploy.md:** раздел «Telegram Mini App»: `/newbot` в BotFather; `TELEGRAM_BOT_TOKEN` в `/opt/devplus/app.env`; Menu Button и Mini App URL `https://<DOMAIN>/tg`; пока токен пуст, вход через Telegram выключен; миграция выполняется сервисом `migrate`.
- [ ] **Step 5: Ручная проверка на телефоне** (после деплоя): открыть бота, пройти привязку, закрыть и открыть заново (вход без GitHub), пройти квиз, прогресс прежний; чужая ссылка привязки показывает чужое имя на странице подтверждения.
- [ ] **Step 6: Update** `docs/roadmap.html` (шаги «План» и «Реализация» подпроекта 11 в `done`, плашка «реализовано», дата), перепубликовать артефакт `https://claude.ai/artifact/5qazb7JVKno2HnYRD7f4Ma`; отметить `- [x]` выполненные шаги в этом файле.
- [x] **Step 7: Commit** `feat(web): phone checks; docs: Telegram Mini App deploy notes, roadmap`.
