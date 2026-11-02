# devplus

Платформа для команды: теория и практика в одном месте. Подробности в `docs/superpowers/specs/`.

## Запуск для разработки

Нужны Docker, [uv](https://docs.astral.sh/uv/), Node 24, pnpm (через `corepack enable`) и make.

```bash
pnpm install
cp .env.example .env     # впиши GitHub OAuth (раздел ниже) и ANTHROPIC_API_KEY, без кавычек: .env читает make
make db                  # Postgres (базы devplus и devplus_test) и Redis в docker
make migrate             # схема БД
make dev                 # api на :8000, web на :3000 и worker
```

Открой http://localhost:3000. Проверка API: `curl http://localhost:8000/api/health` отвечает `{"status":"ok"}`.

`make dev` сам вызывает `make db` и `make migrate`, так что в следующий раз хватит одного `make dev`.

Worker (`make worker`) исполняет прогоны оценщика: API кладёт задачу в Redis, worker её берёт. Без worker прогон остаётся в статусе `queued`. Для настоящих прогонов положи ключ Anthropic API в `.env` (`ANTHROPIC_API_KEY`). `EVALS_LLM_BACKEND=fake` подменяет Claude фейком, ключ тогда не нужен. `EVALS_LLM_BACKEND=claude_cli` гонит вызовы через `claude -p` под твоим входом в Claude Code (подписка, ключ не нужен): только для локальной машины, на сервере остаётся `anthropic`. Токены считаются приблизительно, стоимость условная по прайсу, лимиты берутся из подписки.

`make evals-smoke` делает один живой вызов Claude (Haiku) и печатает ответ, токены и стоимость. Нужен `ANTHROPIC_API_KEY` или `EVALS_LLM_BACKEND=claude_cli`, в CI эта проверка не входит.

`make code-review-smoke` отправляет эталонное ревью задачи Code Review живому Claude и печатает баллы. Нужен `ANTHROPIC_API_KEY` или `EVALS_LLM_BACKEND=claude_cli`, в CI эта проверка не входит. `make check-images` проверяет, что в web-образе нет скрытых частей задач (`task.yaml`, `reference_review.yaml`, `code/`).

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
