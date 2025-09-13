# Development-friendly Dockerfile for NoteMesh backend
FROM python:3.11-slim

# Set build arguments
ARG APP_ENV=development

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements files
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    if [ "$APP_ENV" = "development" ]; then \
        pip install --no-cache-dir -r requirements-dev.txt; \
    fi

# Copy application source code
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "notemesh.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]