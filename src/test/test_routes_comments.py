"""Tests for comments route endpoints."""

import pytest
from unittest.mock import patch


@pytest.mark.route
def test_list_comments(app_client, sample_comment):
    """GET /api/waywo-comments returns paginated comments."""
    with (
        patch("src.routes.comments.get_all_comments", return_value=[sample_comment]),
        patch("src.routes.comments.get_total_comment_count", return_value=1),
    ):
        response = app_client.get("/api/waywo-comments")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["comments"]) == 1
        assert data["comments"][0]["id"] == 111


@pytest.mark.route
def test_list_comments_with_post_filter(app_client, sample_comment):
    """GET /api/waywo-comments?post_id=X filters by post."""
    with (
        patch("src.routes.comments.get_all_comments", return_value=[sample_comment]),
        patch("src.routes.comments.get_total_comment_count", return_value=1),
    ):
        response = app_client.get("/api/waywo-comments?post_id=12345")

        assert response.status_code == 200
        data = response.json()
        assert data["post_id"] == 12345


@pytest.mark.route
def test_get_comment(app_client, sample_comment, sample_post, sample_project):
    """GET /api/waywo-comments/{id} returns comment with projects."""
    with (
        patch("src.routes.comments.get_comment", return_value=sample_comment),
        patch("src.routes.comments.get_post", return_value=sample_post),
        patch(
            "src.routes.comments.get_projects_for_comment",
            return_value=[sample_project],
        ),
    ):
        response = app_client.get("/api/waywo-comments/111")

        assert response.status_code == 200
        data = response.json()
        assert data["comment"]["id"] == 111
        assert data["parent_post"]["id"] == 12345
        assert len(data["projects"]) == 1


@pytest.mark.route
def test_get_comment_not_found(app_client):
    """GET /api/waywo-comments/{id} returns 404 for missing comment."""
    with patch("src.routes.comments.get_comment", return_value=None):
        response = app_client.get("/api/waywo-comments/99999")

        assert response.status_code == 404


@pytest.mark.route
def test_process_single_comment(app_client, sample_comment, mock_celery_result):
    """POST /api/waywo-comments/{id}/process enqueues comment processing."""
    with (
        patch("src.routes.comments.get_comment", return_value=sample_comment),
        patch("src.routes.comments.process_waywo_comment") as mock_task,
    ):
        mock_task.delay.return_value = mock_celery_result

        response = app_client.post("/api/waywo-comments/111/process")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "task_queued"
        assert data["comment_id"] == 111
        mock_task.delay.assert_called_once_with(comment_id=111)


@pytest.mark.route
def test_process_single_comment_not_found(app_client):
    """POST /api/waywo-comments/{id}/process returns 404 for missing comment."""
    with patch("src.routes.comments.get_comment", return_value=None):
        response = app_client.post("/api/waywo-comments/99999/process")

        assert response.status_code == 404
