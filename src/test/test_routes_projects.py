"""Tests for projects route endpoints."""

import pytest
from unittest.mock import patch


@pytest.mark.route
def test_list_projects(app_client, sample_project):
    """GET /api/waywo-projects returns paginated projects."""
    with (
        patch("src.routes.projects.get_all_projects", return_value=[sample_project]),
        patch("src.routes.projects.get_total_project_count", return_value=1),
        patch("src.routes.projects.get_bookmarked_count", return_value=0),
    ):
        response = app_client.get("/api/waywo-projects")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["projects"]) == 1
        assert data["projects"][0]["title"] == "Cool Project"


@pytest.mark.route
def test_list_projects_by_comment(app_client, sample_project):
    """GET /api/waywo-projects?comment_id=X filters by comment."""
    with (
        patch(
            "src.routes.projects.get_projects_for_comment",
            return_value=[sample_project],
        ),
        patch("src.routes.projects.get_bookmarked_count", return_value=0),
    ):
        response = app_client.get("/api/waywo-projects?comment_id=111")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1


@pytest.mark.route
def test_list_projects_with_score_filters(app_client, sample_project):
    """GET /api/waywo-projects with score filters."""
    with (
        patch("src.routes.projects.get_all_projects", return_value=[sample_project]),
        patch("src.routes.projects.get_total_project_count", return_value=1),
        patch("src.routes.projects.get_bookmarked_count", return_value=0),
    ):
        response = app_client.get(
            "/api/waywo-projects?min_idea_score=5&max_idea_score=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["min_idea_score"] == 5
        assert data["filters"]["max_idea_score"] == 10


@pytest.mark.route
def test_get_project(app_client, sample_project, sample_comment, sample_post):
    """GET /api/waywo-projects/{id} returns project with source info."""
    with (
        patch("src.routes.projects.get_project", return_value=sample_project),
        patch("src.routes.projects.get_comment", return_value=sample_comment),
        patch("src.routes.projects.get_post", return_value=sample_post),
    ):
        response = app_client.get("/api/waywo-projects/1")

        assert response.status_code == 200
        data = response.json()
        assert data["project"]["title"] == "Cool Project"
        assert data["source_comment"]["id"] == 111
        assert data["parent_post"]["id"] == 12345


@pytest.mark.route
def test_get_project_not_found(app_client):
    """GET /api/waywo-projects/{id} returns 404 for missing project."""
    with patch("src.routes.projects.get_project", return_value=None):
        response = app_client.get("/api/waywo-projects/99999")

        assert response.status_code == 404


@pytest.mark.route
def test_delete_project(app_client):
    """DELETE /api/waywo-projects/{id} deletes a project."""
    with patch("src.routes.projects.delete_project", return_value=True):
        response = app_client.delete("/api/waywo-projects/1")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"


@pytest.mark.route
def test_delete_project_not_found(app_client):
    """DELETE /api/waywo-projects/{id} returns 404 for missing project."""
    with patch("src.routes.projects.delete_project", return_value=False):
        response = app_client.delete("/api/waywo-projects/99999")

        assert response.status_code == 404


@pytest.mark.route
def test_toggle_bookmark(app_client):
    """POST /api/waywo-projects/{id}/bookmark toggles bookmark."""
    with patch("src.routes.projects.toggle_bookmark", return_value=True):
        response = app_client.post("/api/waywo-projects/1/bookmark")

        assert response.status_code == 200
        data = response.json()
        assert data["is_bookmarked"] is True
        assert data["project_id"] == 1


@pytest.mark.route
def test_toggle_bookmark_not_found(app_client):
    """POST /api/waywo-projects/{id}/bookmark returns 404 for missing project."""
    with patch("src.routes.projects.toggle_bookmark", return_value=None):
        response = app_client.post("/api/waywo-projects/99999/bookmark")

        assert response.status_code == 404


@pytest.mark.route
def test_get_similar_projects(app_client, sample_project, sample_project_2):
    """GET /api/waywo-projects/{id}/similar returns similar projects."""
    with (
        patch("src.routes.projects.get_project", return_value=sample_project),
        patch(
            "src.routes.projects.get_similar_projects",
            return_value=[(sample_project_2, 0.85)],
        ),
    ):
        response = app_client.get("/api/waywo-projects/1/similar")

        assert response.status_code == 200
        data = response.json()
        assert len(data["similar_projects"]) == 1
        assert data["similar_projects"][0]["similarity"] == 0.85


@pytest.mark.route
def test_list_hashtags(app_client):
    """GET /api/waywo-projects/hashtags returns unique hashtags."""
    with patch(
        "src.routes.projects.get_all_hashtags",
        return_value=["ai", "python", "rust", "web"],
    ):
        response = app_client.get("/api/waywo-projects/hashtags")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4
        assert "python" in data["hashtags"]
