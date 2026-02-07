#!/usr/bin/env python3
"""Healthcheck script for Celery worker and beat."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from src.worker.app import celery_app

    # Simple check: verify we can connect to the broker
    celery_app.backend.client.ping()
    sys.exit(0)
except Exception:
    sys.exit(1)
