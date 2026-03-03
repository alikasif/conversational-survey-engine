# --- Builder stage ---
FROM python:3.11-slim AS builder

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# --- Runtime stage ---
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/

# Mount point for Google credentials
RUN mkdir -p /app/credentials

# Create non-root user
RUN useradd --create-home appuser
USER appuser

# Environment variables (overridden at runtime)
ENV GEMINI_API_KEY="" \
    GEMINI_MODEL="vertex_ai/gemini-2.0-flash" \
    GEMINI_VALIDATOR_MODEL="gemini/gemini-2.0-flash" \
    GOOGLE_APPLICATION_CREDENTIALS="" \
    LOG_LEVEL="info"

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
