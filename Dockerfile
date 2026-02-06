# Multi-stage Dockerfile for waywo backend
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/app/.venv/bin:$PATH"

ARG DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get clean && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy dependency files first (for better caching)
COPY pyproject.toml LICENSE ./

# Install uv and create venv
RUN pip install --no-cache-dir uv && uv venv

# Copy source code (excluding media files via .dockerignore)
COPY --chown=app:app src/ ./src

COPY --chown=app:app src/healthcheck.py /app/healthcheck.py

# Install your package + dev extras + notebook in editable mode
RUN . .venv/bin/activate && \
    uv pip install -e . && \
    uv pip install -e ".[dev]" && \
    uv pip install -e ".[notebook]"

# Create directories for celery and media with proper permissions
# Do this after copying source code to ensure directories exist
RUN mkdir -p /app/celery-data /app/media && \
    chown -R app:app /app/celery-data /app/media

USER app

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD ["python","/app/healthcheck.py"]

# Expose port
EXPOSE 8000

# Default command
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]