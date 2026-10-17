# devplus

Платформа для команды: теория и практика в одном месте. Подробности в `docs/superpowers/specs/`.

## Запуск для разработки

Нужны Docker, [uv](https://docs.astral.sh/uv/), Node 24, pnpm (через `corepack enable`) и make.

```bash
pnpm install
cp .env.example .env     # впиши GitHub OAuth (раздел ниже), без кавычек: .env читает make
make db                  # Postgres в docker (базы devplus и devplus_test)
make migrate             # схема БД
make dev                 # api на :8000 и web на :3000
```

Открой http://localhost:3000. Проверка API: `curl http://localhost:8000/api/health` отвечает `{"status":"ok"}`.

`make dev` сам вызывает `make db` и `make migrate`, так что в следующий раз хватит одного `make dev`.

## Тесты и линтеры

```bash
make test
make lint
pnpm --filter web exec playwright install chromium   # один раз
make e2e
```

Тестам API нужен запущенный `make db`, e2e дополнительно нужен `make migrate`. Перед `make e2e` освободи порты 3000 и 8000.

## OAuth-приложение GitHub для разработки

1. GitHub → Settings → Developer settings → OAuth Apps → New OAuth App.
2. Homepage URL: `http://localhost:3000`.
3. Authorization callback URL: `http://localhost:3000/api/auth/github/callback`.
4. Client ID и сгенерированный Client secret положи в `.env` (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`).
5. Свой логин добавь в `ALLOWED_GITHUB_LOGINS` (через запятую, без учёта регистра).

## Деплой

Один VPS, образы из GHCR, выкладка из GitHub Actions после зелёного CI. Настройка сервера и откат: `docs/deploy.md`.
