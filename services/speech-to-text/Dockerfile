# Stage 1: Base image with Python
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/root/.cache/huggingface \
    HF_TOKEN=${HF_TOKEN:-}

# Install system dependencies required for nemo_toolkit and audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Stage 2: Build stage with uv for fast dependency installation
FROM base AS builder

# Install uv for fast Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy only dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies
RUN uv venv /app/.venv && \
    VIRTUAL_ENV=/app/.venv uv sync --frozen && \
    rm -rf /root/.cache/uv

# Stage 3: Production image
FROM base AS production

# Copy virtual environment from builder (with correct ownership)
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Set PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code with correct ownership
COPY --chown=app:app main.py index.html ./

# Switch to non-root user
USER app

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
