# devplus

Платформа для команды: от «что такое интернет» до system design, highload и AI engineering. Теория и практика (код, схемы, промпты) в одном месте.

- Спецификация обзора и ядра: `docs/superpowers/specs/2026-10-18-devplus-overview-core-design.md`
- Дорожная карта: `docs/roadmap.html`. После каждого утверждённого шага обновляй её и перепубликуй артефакт.

## Общение

Отвечай по-русски и обращайся на «ты». Технические термины оставляй на английском (FastAPI, harness, evals).

## Прогресс между сессиями

- Команда `/continue` восстанавливает, где остановилась работа, и предлагает следующий шаг.
- Каждый переход стадии сразу фиксируй в репозитории и коммить:
  - статус в шапке спеки (`**Статус:** утверждена <дата>`);
  - выполненные шаги плана (`- [x]`);
  - `docs/roadmap.html`, после чего перепубликуй артефакт.
- Решение, которое есть только в чате, следующая сессия не увидит.

## Стек

- `apps/web`: Next.js (App Router), TypeScript, Tailwind, shadcn/ui, pnpm
- `apps/api`: FastAPI, Pydantic v2, SQLAlchemy 2 async + asyncpg, Alembic, dishka, uv
- PostgreSQL. Redis и worker (Taskiq) исполняют прогоны оценщика промптов; LLM в оценщике только Claude (`ANTHROPIC_API_KEY`; локально можно `EVALS_LLM_BACKEND=claude_cli`: вызовы идут через `claude -p` под входом Claude Code, на сервере так нельзя).
- Деплой: docker-compose на одном VPS, Caddy впереди

## Команды

```
make dev           # Postgres и Redis в docker, api, web и worker напрямую на машине
make db            # только Postgres и Redis в docker
make api           # API на :8000
make web           # Next.js dev-сервер
make worker        # Taskiq worker: исполняет прогоны оценщика, без него они висят в queued
make test          # pytest + vitest
make lint          # ruff, mypy, import-linter, eslint, prettier, tsc
make gen-client    # TS-клиент из OpenAPI в packages/api-client
make migrate       # alembic upgrade head
make migrate-check # alembic check: модели и миграции совпадают
make e2e           # Playwright
make evals-smoke   # живой вызов Claude: ANTHROPIC_API_KEY или EVALS_LLM_BACKEND=claude_cli, в CI не входит
make code-review-smoke  # то же, живой судья на реальной задаче
make check-images  # в web-образе нет скрытых частей задач Code Review
```

Деплой и откат: `docs/deploy.md`.

## Правила

- **Процесс.** Новый подпроект или модуль контента: брейнсторм → спецификация → план → реализация. Без утверждённой спецификации код не пишем.
- **ponytail.** Минимальное полное изменение, без кода «на будущее». Известное ограничение помечай комментарием `shortcut: <ограничение>, <когда менять>`. Валидацию, безопасность и обработку ошибок не урезай.
- **TDD** для нетривиальной логики.
- **Модули бэкенда** (`apps/api/app/modules/<name>/`): `router.py`, `service.py`, `models.py`, `schemas.py`, `providers.py`. Модуль импортирует из другого модуля только `service`. Это проверяет import-linter.
- **Модули оценщика.** `evals`: движок и Лаборатория (промпты, датасеты, прогоны, оценщики). `review`: Ревью промптов. `trainer`: Тренажёр, задачи лежат файлами в `content/<NN-модуль>/tasks/` (`.yaml` со скрытыми кейсами читает только API, `.mdx` с условием). `review` и `trainer` создают прогоны только через `evals.service`.
- **Модуль Code Review.** `code_review`: Code Review, задачи папками в `content/<NN-модуль>/tasks/<slug>/` (скрытые `task.yaml`, `reference_review.yaml`, `code/` читает только API, в web-образ они не попадают), оценка только через `evals.service`.
- **Модуль симулятора.** `simulator`: симулятор system design, расчёт нагрузки в `engine/`, задачи парами файлов в `content/<NN-модуль>/simulator/` (`NN-slug.yaml` со скрытыми целями сценариев, `review.reference` и `reference_graph` читает только API, в web-образ он не попадает; `NN-slug.mdx` с условием), AI-разбор только через `evals.service`.
- **DI только через dishka.** Сервисы не собираются через цепочки FastAPI `Depends`. Каждый модуль объявляет свой `Provider`.
- **Ошибки.** Сервисы бросают доменные исключения, в HTTP их переводит `core/errors.py`. Формат ответа `{"detail": "..."}`.
- **API.** После изменения API запусти `make gen-client` и закоммить сгенерированный клиент.
- **Миграции** только через Alembic. Сгенерированную миграцию читай глазами перед коммитом.
- **Уроки** лежат в `content/<NN-модуль>/<NN-урок>.mdx`. Во frontmatter `title` и `summary`. Шаблон урока из 6 разделов описан в разделе 4 спецификации.
- **Секреты** хранятся только в `.env`, файл не в git. При добавлении переменной обнови `.env.example`. Файлы `.env` не читай.
