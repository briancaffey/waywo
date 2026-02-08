"""Tests for admin route endpoints."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import httpx


@pytest.mark.route
def test_admin_stats(app_client):
    """GET /api/admin/stats returns database and Redis stats."""
    mock_stats = {
        "posts_count": 10,
        "comments_count": 50,
        "projects_count": 30,
        "processed_comments_count": 45,
        "valid_projects_count": 25,
        "projects_with_embeddings_count": 20,
    }
    mock_redis = MagicMock()
    mock_redis.info.return_value = {"used_memory_human": "1.5M"}
    mock_redis.dbsize.return_value = 100

    with (
        patch("src.routes.admin.get_database_stats", return_value=mock_stats),
        patch("redis.from_url", return_value=mock_redis),
    ):
        response = app_client.get("/api/admin/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["posts_count"] == 10
        assert data["redis_connected"] is True
        assert data["redis_keys_count"] == 100


@pytest.mark.route
def test_admin_stats_redis_down(app_client):
    """GET /api/admin/stats handles Redis connection failure."""
    mock_stats = {
        "posts_count": 10,
        "comments_count": 50,
        "projects_count": 30,
        "processed_comments_count": 45,
        "valid_projects_count": 25,
        "projects_with_embeddings_count": 20,
    }

    with (
        patch("src.routes.admin.get_database_stats", return_value=mock_stats),
        patch("redis.from_url", side_effect=Exception("Connection refused")),
    ):
        response = app_client.get("/api/admin/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["redis_connected"] is False


@pytest.mark.route
def test_services_health(app_client):
    """GET /api/admin/services-health checks external services."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"id": "test-model"}]}

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        response = app_client.get("/api/admin/services-health")

        assert response.status_code == 200
        data = response.json()
        # All services should be checked
        assert "llm" in data
        assert "embedder" in data
        assert "reranker" in data


@pytest.mark.route
def test_reset_sqlite(app_client):
    """DELETE /api/admin/reset-sqlite clears database."""
    mock_result = {
        "projects_deleted": 5,
        "comments_deleted": 10,
        "posts_deleted": 2,
    }
    with patch("src.routes.admin.reset_all_data", return_value=mock_result):
        response = app_client.delete("/api/admin/reset-sqlite")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["projects_deleted"] == 5


@pytest.mark.route
def test_reset_sqlite_error(app_client):
    """DELETE /api/admin/reset-sqlite handles errors."""
    with patch(
        "src.routes.admin.reset_all_data",
        side_effect=Exception("DB locked"),
    ):
        response = app_client.delete("/api/admin/reset-sqlite")

        assert response.status_code == 500


@pytest.mark.route
def test_rebuild_vector_index(app_client):
    """POST /api/admin/rebuild-vector-index rebuilds index."""
    with patch("src.db.database.build_vector_index"):
        response = app_client.post("/api/admin/rebuild-vector-index")

        assert response.status_code == 200
        assert response.json()["status"] == "success"


@pytest.mark.route
def test_workflow_prompts(app_client):
    """GET /api/workflow-prompts returns workflow step prompts."""
    import sys

    # Create a mock module for src.workflows.prompts since the real one
    # may fail to import due to heavy LlamaIndex dependencies
    mock_prompts_module = MagicMock()
    mock_prompts_module.WORKFLOW_STEPS = [
        {"name": "extract", "prompt": "Extract projects..."},
        {"name": "validate", "prompt": "Validate project..."},
    ]

    with patch.dict(sys.modules, {"src.workflows.prompts": mock_prompts_module}):
        response = app_client.get("/api/workflow-prompts")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
