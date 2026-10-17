-include .env
export

.PHONY: db api test-api lint-api test lint

db:
	docker compose -f infra/docker-compose.dev.yml up -d --wait

api:
	cd apps/api && uv run uvicorn app.main:app --reload --port 8000

test-api:
	cd apps/api && uv run pytest

lint-api:
	cd apps/api && uv run ruff check
	cd apps/api && uv run ruff format --check
	cd apps/api && uv run mypy

test: test-api

lint: lint-api
