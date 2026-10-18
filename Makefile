-include .env
export

.PHONY: db api web dev migrate migrate-check gen-client test-api test-web e2e lint-api lint-web test lint

db:
	docker compose -f infra/docker-compose.dev.yml up -d --wait

api:
	cd apps/api && uv run uvicorn app.main:app --reload --port 8000

web:
	pnpm --filter web dev

dev: db migrate
	$(MAKE) -j2 api web

migrate:
	cd apps/api && uv run alembic upgrade head

migrate-check:
	cd apps/api && uv run alembic check

gen-client:
	cd apps/api && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > ../../packages/api-client/openapi.json
	pnpm --filter @devplus/api-client exec openapi-typescript openapi.json -o src/schema.d.ts

test-api:
	cd apps/api && uv run pytest

test-web:
	pnpm --filter web exec vitest run

e2e:
	pnpm --filter web exec playwright test

lint-api:
	cd apps/api && uv run ruff check
	cd apps/api && uv run ruff format --check
	cd apps/api && uv run mypy
	cd apps/api && uv run lint-imports

lint-web:
	pnpm --filter web lint && pnpm --filter web format:check && pnpm --filter web exec next typegen && pnpm --filter web exec tsc --noEmit

test: test-api test-web

lint: lint-api lint-web
