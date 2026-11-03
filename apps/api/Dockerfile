FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.21 /uv /bin/uv
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1 CONTENT_DIR=/app/content
# Context is the repo root (the image ships the trainer tasks); Dockerfile.dockerignore filters it.
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev
COPY apps/api .
# Only content/*/tasks/** and content/*/simulator/*.{yaml,mdx} get here: the API reads the hidden cases and the frontmatter.
COPY content /app/content
USER nobody
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
