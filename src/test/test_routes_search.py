"""Tests for search route endpoints."""

import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.route
def test_embedding_health_healthy(app_client):
    """GET /api/embedding/health returns healthy status."""
    with patch(
        "src.routes.search.check_embedding_service_health",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = app_client.get("/api/embedding/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.route
def test_embedding_health_unhealthy(app_client):
    """GET /api/embedding/health returns 503 when service is down."""
    with patch(
        "src.routes.search.check_embedding_service_health",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = app_client.get("/api/embedding/health")

        assert response.status_code == 503
        assert response.json()["status"] == "unhealthy"


@pytest.mark.route
def test_rerank_health_healthy(app_client):
    """GET /api/rerank/health returns healthy status."""
    with patch(
        "src.routes.search.check_rerank_service_health",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = app_client.get("/api/rerank/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.route
def test_rerank_health_unhealthy(app_client):
    """GET /api/rerank/health returns 503 when service is down."""
    with patch(
        "src.routes.search.check_rerank_service_health",
        new_callable=AsyncMock,
        return_value=False,
    ):
        response = app_client.get("/api/rerank/health")

        assert response.status_code == 503


@pytest.mark.route
def test_semantic_search_stats(app_client):
    """GET /api/semantic-search/stats returns embedding coverage stats."""
    with (
        patch("src.routes.search.get_total_project_count", return_value=100),
        patch("src.routes.search.get_projects_with_embeddings_count", return_value=80),
    ):
        response = app_client.get("/api/semantic-search/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_projects"] == 100
        assert data["projects_with_embeddings"] == 80
        assert data["embedding_coverage"] == 80.0


@pytest.mark.route
def test_semantic_search_stats_empty(app_client):
    """GET /api/semantic-search/stats handles zero projects."""
    with (
        patch("src.routes.search.get_total_project_count", return_value=0),
        patch("src.routes.search.get_projects_with_embeddings_count", return_value=0),
    ):
        response = app_client.get("/api/semantic-search/stats")

        assert response.status_code == 200
        assert response.json()["embedding_coverage"] == 0


@pytest.mark.route
def test_semantic_search(app_client, sample_project, fake_embedding):
    """POST /api/semantic-search performs vector search."""
    with (
        patch(
            "src.routes.search.get_single_embedding",
            new_callable=AsyncMock,
            return_value=fake_embedding,
        ),
        patch(
            "src.routes.search.semantic_search",
            return_value=[(sample_project, 0.92)],
        ),
        patch(
            "src.routes.search.rerank_documents",
            new_callable=AsyncMock,
            side_effect=Exception("skip rerank"),
        ),
    ):
        response = app_client.post(
            "/api/semantic-search",
            json={"query": "python web project", "limit": 5, "use_rerank": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "python web project"
        assert len(data["results"]) == 1
        assert data["results"][0]["similarity"] == 0.92


@pytest.mark.route
def test_semantic_search_embedding_error(app_client):
    """POST /api/semantic-search returns 503 when embedding service fails."""
    from src.clients.embedding import EmbeddingError

    with patch(
        "src.routes.search.get_single_embedding",
        new_callable=AsyncMock,
        side_effect=EmbeddingError("Service unavailable"),
    ):
        response = app_client.post(
            "/api/semantic-search",
            json={"query": "test query"},
        )

        assert response.status_code == 503
