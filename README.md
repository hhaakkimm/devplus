# devplus

Платформа для команды: теория и практика в одном месте. Подробности в `docs/superpowers/specs/`.

## Запуск для разработки

Нужны Docker, [uv](https://docs.astral.sh/uv/) и make.

```bash
make db                  # Postgres в docker (базы devplus и devplus_test)
cp .env.example .env
make api                 # API на http://localhost:8000
```

`.env` пишется без кавычек: его читает make.

Проверка: `curl http://localhost:8000/api/health` отвечает `{"status":"ok"}`.

## Тесты и линтеры

```bash
make test
make lint
```

Тестам API нужен запущенный `make db`.

## OAuth-приложение GitHub для разработки

1. GitHub → Settings → Developer settings → OAuth Apps → New OAuth App.
2. Homepage URL: `http://localhost:3000`.
3. Authorization callback URL: `http://localhost:3000/api/auth/github/callback`.
4. Client ID и сгенерированный Client secret положи в `.env` (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`).
5. Свой логин добавь в `ALLOWED_GITHUB_LOGINS` (через запятую, без учёта регистра).
