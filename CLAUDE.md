# devplus

Платформа для команды: от «что такое интернет» до system design, highload и AI engineering. Теория и практика (код, схемы, промпты) в одном месте.

- Спецификация обзора и ядра: `docs/superpowers/specs/2026-10-18-devplus-overview-core-design.md`
- Дорожная карта: `docs/roadmap.html`. После каждого утверждённого шага обновляй её и перепубликуй артефакт.

## Общение

Отвечай по-русски. Технические термины оставляй на английском (FastAPI, harness, evals).

## Статус

Код ещё не написан. Команды и структура ниже взяты из спецификации. Прежде чем на них полагаться, проверь, что они уже существуют.

## Стек

- `apps/web`: Next.js (App Router), TypeScript, Tailwind, shadcn/ui, pnpm
- `apps/api`: FastAPI, Pydantic v2, SQLAlchemy 2 async + asyncpg, Alembic, dishka, uv
- PostgreSQL. Redis и worker появятся вместе с оценщиком промптов.
- Деплой: docker-compose на одном VPS, Caddy впереди

## Команды (появятся с ядром)

```
make dev         # Postgres в docker, api и web напрямую на машине
make test        # pytest + vitest
make lint        # ruff, mypy, import-linter, eslint, tsc
make gen-client  # TS-клиент из OpenAPI в packages/api-client
make migrate     # alembic upgrade head
```

## Правила

- **Процесс.** Новый подпроект или модуль контента: брейнсторм → спецификация → план → реализация. Без утверждённой спецификации код не пишем.
- **ponytail.** Минимальное полное изменение, без кода «на будущее». Известное ограничение помечай комментарием `shortcut: <ограничение>, <когда менять>`. Валидацию, безопасность и обработку ошибок не урезай.
- **TDD** для нетривиальной логики.
- **Модули бэкенда** (`apps/api/app/modules/<name>/`): `router.py`, `service.py`, `models.py`, `schemas.py`, `providers.py`. Модуль импортирует из другого модуля только `service`. Это проверяет import-linter.
- **DI только через dishka.** Сервисы не собираются через цепочки FastAPI `Depends`. Каждый модуль объявляет свой `Provider`.
- **Ошибки.** Сервисы бросают доменные исключения, в HTTP их переводит `core/errors.py`. Формат ответа `{"detail": "..."}`.
- **API.** После изменения API запусти `make gen-client` и закоммить сгенерированный клиент.
- **Миграции** только через Alembic. Сгенерированную миграцию читай глазами перед коммитом.
- **Уроки** лежат в `content/<NN-модуль>/<NN-урок>.mdx`. Во frontmatter `title` и `summary`. Шаблон урока из 6 разделов описан в разделе 4 спецификации.
- **Секреты** хранятся только в `.env`, файл не в git. При добавлении переменной обнови `.env.example`. Файлы `.env` не читай.
