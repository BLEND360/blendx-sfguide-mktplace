# ---------- Base ----------
FROM python:3.10-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/tmp/uv-cache

WORKDIR /app

# ---------- Builder ----------
FROM base AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

# ---------- Runtime ----------
FROM base AS runtime

# Install curl for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy uv from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependencies and app
COPY --from=builder /app /app
COPY . /app

EXPOSE 8081

# Gunicorn config via env
ENV GUNICORN_WORKERS=4 \
    GUNICORN_THREADS=4 \
    GUNICORN_TIMEOUT=0 \
    GUNICORN_KEEPALIVE=650

STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8081/health || exit 1

ENTRYPOINT ["sh", "-c", "\
  uv run gunicorn app.main:app \
  --workers ${GUNICORN_WORKERS} \
  --worker-class uvicorn.workers.UvicornWorker \
  --threads ${GUNICORN_THREADS} \
  --timeout ${GUNICORN_TIMEOUT} \
  --keep-alive ${GUNICORN_KEEPALIVE} \
  --bind 0.0.0.0:8081 \
"]
