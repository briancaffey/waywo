FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/

# Install nvidia-nat with langchain extra (required for chat_completion workflow)
RUN uv pip install --system --no-cache-dir "nvidia-nat[langchain]"

# Install the local package for custom components
RUN uv pip install --system --no-cache-dir -e .

# Copy workflow configuration
COPY workflow.yml .

EXPOSE 8080

CMD ["nat", "serve", "--config_file", "/app/workflow.yml"]
