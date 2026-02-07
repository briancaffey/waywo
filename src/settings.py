"""Centralized configuration from environment variables."""

import os

# Redis / Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# External services
EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://192.168.5.96:8000")
RERANK_URL = os.getenv("RERANK_URL", "http://192.168.5.173:8111")
FIRECRAWL_URL = os.getenv("FIRECRAWL_URL", "http://localhost:3002")
FIRECRAWL_TIMEOUT = int(os.getenv("FIRECRAWL_TIMEOUT", "30"))
FIRECRAWL_MAX_RETRIES = int(os.getenv("FIRECRAWL_MAX_RETRIES", "3"))
FIRECRAWL_MAX_CONTENT_LENGTH = int(os.getenv("FIRECRAWL_MAX_CONTENT_LENGTH", "10000"))

# LLM
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://192.168.6.19:8002/v1")
LLM_MODEL_NAME = os.getenv(
    "LLM_MODEL_NAME", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4"
)
LLM_API_KEY = os.getenv("LLM_API_KEY", "not-needed")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

# Data and media directories
DATA_DIR = os.getenv("DATA_DIR", "/app/data")
MEDIA_DIR = os.getenv("MEDIA_DIR", "/app/media")

# Phoenix observability
PHOENIX_HOST = os.getenv("PHOENIX_HOST", "localhost")
PHOENIX_PORT = os.getenv("PHOENIX_PORT", "6006")
