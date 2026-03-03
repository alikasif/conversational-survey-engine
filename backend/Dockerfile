# --- Builder stage ---
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies for asyncpg (needs libpq-dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# --- Runtime stage ---
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependency for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN useradd --create-home appuser
USER appuser

# Environment variables (overridden at runtime)
ENV DATABASE_URL="" \
    LLM_SERVICE_URL="http://llm-service:8001" \
    CORS_ORIGINS='["*"]' \
    LOG_LEVEL="info"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
