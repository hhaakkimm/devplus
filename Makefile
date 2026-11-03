-include .env
export

.PHONY: db api web worker dev migrate migrate-check gen-client test-api test-web e2e evals-smoke code-review-smoke lint-api lint-web test lint check-images

db:
	docker compose -f infra/docker-compose.dev.yml up -d --wait

api:
	cd apps/api && uv run uvicorn app.main:app --reload --port 8000

web:
	pnpm --filter web dev

# one process: taskiq starts 2 by default, which would run 4 runs at once and race on start-up recovery
worker:
	cd apps/api && uv run taskiq worker app.worker:broker --workers 1 --max-async-tasks 2

dev: db migrate
	$(MAKE) -j3 api web worker

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

# live call to Claude, needs ANTHROPIC_API_KEY or EVALS_LLM_BACKEND=claude_cli; not part of CI
evals-smoke:
	cd apps/api && uv run python scripts/evals_smoke.py

# live call to Claude, needs ANTHROPIC_API_KEY or EVALS_LLM_BACKEND=claude_cli; not part of CI
code-review-smoke:
	cd apps/api && uv run python scripts/code_review_smoke.py

lint-web:
	pnpm --filter web lint && pnpm --filter web format:check && pnpm --filter web exec next typegen && pnpm --filter web exec tsc --noEmit

test: test-api test-web

lint: lint-api lint-web

# Builds both images as deploy does (repo root as context) and checks what content they carry:
# the web image has no file below tasks/<slug>/ and no hidden trainer .yaml (but still its lessons and
# trainer .mdx), the API image has every task.yaml of the repo. A failed docker run fails the target.
check-images:
	docker build -f apps/web/Dockerfile -t devplus-web-check .
	docker build -f apps/api/Dockerfile -t devplus-api-check .
	@web=$$(docker run --rm --entrypoint sh devplus-web-check -c "find /app/content -type f") || exit 1; \
	for f in 00-start/01-how-to-use.mdx 00-start/tasks/01-iso-dates.mdx 10-system-design/simulator/01-url-shortener.mdx; do \
		echo "$$web" | grep -qx "/app/content/$$f" || { echo "web image lost /app/content/$$f"; exit 1; }; \
	done; \
	leaked=$$(echo "$$web" | grep -E '/tasks/[^/]+/|/tasks/[^/]*\.yaml$$|/simulator/[^/]*\.yaml$$'); \
	if [ -n "$$leaked" ]; then echo "web image carries hidden task files:"; echo "$$leaked"; exit 1; fi
	@raw=$$(docker run --rm --entrypoint sh devplus-api-check -c "find /app/content -path '*/tasks/*/task.yaml'") || exit 1; \
	have=$$(echo "$$raw" | sed 's|^/app/||' | sort); \
	want=$$(find content -path '*/tasks/*/task.yaml' | sort); \
	if [ "$$have" != "$$want" ]; then echo "API image task.yaml mismatch"; echo "repo:"; echo "$$want"; echo "image:"; echo "$$have"; exit 1; fi; \
	if [ -z "$$want" ]; then echo "API half: no code review task in the repo, nothing compared"; fi
	@raw=$$(docker run --rm --entrypoint sh devplus-api-check -c "find /app/content -path '*/simulator/*' \( -name '*.yaml' -o -name '*.mdx' \) -type f") || exit 1; \
	have=$$(echo "$$raw" | sed 's|^/app/||' | sort); \
	want=$$(find content -path '*/simulator/*' \( -name '*.yaml' -o -name '*.mdx' \) -type f | sort); \
	if [ -z "$$want" ]; then echo "no simulator task in the repo, the probe would pass vacuously"; exit 1; fi; \
	if [ "$$have" != "$$want" ]; then echo "API image simulator files mismatch"; echo "repo:"; echo "$$want"; echo "image:"; echo "$$have"; exit 1; fi; \
	for f in $$want; do \
		case $$f in *.yaml) docker run --rm --entrypoint cat devplus-api-check /app/$$f | cmp -s - $$f || { echo "API image $$f differs from the repo"; exit 1; };; esac; \
	done
	@echo "check-images: ok"
