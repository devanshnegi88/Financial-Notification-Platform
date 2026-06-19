# ─── Base Stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ─── Dependencies Stage ──────────────────────────────────────────────────────
FROM base AS dependencies

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ─── Development Stage ───────────────────────────────────────────────────────
FROM dependencies AS development

COPY . .

RUN mkdir -p /var/log/fnp && \
    chmod 755 /var/log/fnp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ─── Production Stage ────────────────────────────────────────────────────────
FROM dependencies AS production

COPY . .

RUN mkdir -p /var/log/fnp && \
    chmod 755 /var/log/fnp && \
    useradd --system --create-home --shell /bin/bash fnpuser && \
    chown -R fnpuser:fnpuser /app /var/log/fnp

USER fnpuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
