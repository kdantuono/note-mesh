# Multi-stage build for NoteMesh backend
FROM python:3.11-slim as builder

# Set build arguments
ARG APP_ENV=production

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

COPY pyproject.toml setup.cfg setup.py ./
COPY requirements.txt requirements-dev.txt ./

# build a wheel for the app and install deps
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip wheel --no-deps --wheel-dir /wheels -r requirements.txt && \
    if [ "$APP_ENV" = "development" ]; then \
        pip wheel --no-deps --wheel-dir /wheels -r requirements-dev.txt; \
    fi && \
    pip wheel --no-deps --wheel-dir /wheels .

FROM python:3.11-slim as production

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r notemesh && useradd -r -g notemesh notemesh

WORKDIR /app

# Install only wheels (no dev tooling)
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy only runtime files (application source)
COPY src ./src
COPY backend/* LICENSE README.md ./

# ensure correct ownership
RUN chown -R notemesh:notemesh /app

USER notemesh

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "notemesh.main:app", "--host", "0.0.0.0", "--port", "8000"]