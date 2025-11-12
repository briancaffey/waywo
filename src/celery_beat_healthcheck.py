#!/usr/bin/env python3
"""Healthcheck script for Celery beat."""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from src.celery_app import celery_app

    # For beat, we just need to verify we can connect to the broker
    # Beat doesn't have an inspect API like workers do
    celery_app.backend.client.ping()
    sys.exit(0)
except Exception:
    # If connection fails, consider unhealthy
    sys.exit(1)
