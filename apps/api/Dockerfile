FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.21 /uv /bin/uv
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
USER nobody
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
