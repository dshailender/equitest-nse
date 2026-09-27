# Stage 1: Dependency builder
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir .

# Stage 2: Production runner
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production \
    DATA_SOURCE=yfinance \
    REPO_ROOT=/app \
    FIXTURES_DIR=/app/data/fixtures \
    BACKTEST_STORAGE_PATH=/app/data/backtests \
    DATABASE_URL=sqlite:////app/data/dev.db

ARG GIT_SHA="unknown"
ENV GIT_SHA=${GIT_SHA}

# Install WeasyPrint and healthcheck system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

# Verify PDF compilation pipeline at build time
RUN python -c "from weasyprint import HTML; pdf = HTML(string='<h1>Smoke Test</h1>').write_pdf(); assert pdf.startswith(b'%PDF'), 'PDF generation smoke test failed'"

# Create non-root application user and group (UID/GID 1001)
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Copy application source
COPY app/ ./app/
COPY pyproject.toml .

# Create all persistence and cache mountpoints with non-root ownership
RUN mkdir -p /app/data/backtests \
             /app/data/reports \
             /app/data/cache \
             /app/data/fixtures && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
