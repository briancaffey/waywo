"""Tests for health and debug endpoints."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.route
def test_root_endpoint(app_client):
    """GET / returns welcome message."""
    response = app_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "what are you working on?"}


@pytest.mark.route
def test_health_endpoint(app_client):
    """GET /api/health returns ok status."""
    response = app_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.route
def test_debug_celery_task(app_client, mock_celery_result):
    """POST /api/debug/celery-task enqueues a debug task."""
    with patch("src.routes.health.debug_task") as mock_task:
        mock_task.apply_async.return_value = mock_celery_result

        response = app_client.post("/api/debug/celery-task")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "task_queued"
        assert data["task_id"] == "test-task-id-12345"
        mock_task.apply_async.assert_called_once()
