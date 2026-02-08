"""Tests for posts route endpoints."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.route
def test_list_posts(app_client, sample_post):
    """GET /api/waywo-posts returns list of posts."""
    with (
        patch("src.routes.posts.get_all_post_ids", return_value=[12345]),
        patch("src.routes.posts.get_post", return_value=sample_post),
        patch("src.routes.posts.get_comment_count_for_post", return_value=3),
    ):
        response = app_client.get("/api/waywo-posts")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 12345
        assert data[0]["comment_count"] == 3


@pytest.mark.route
def test_list_posts_empty(app_client):
    """GET /api/waywo-posts returns empty list when no posts."""
    with patch("src.routes.posts.get_all_post_ids", return_value=[]):
        response = app_client.get("/api/waywo-posts")

        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.route
def test_get_post(app_client, sample_post, sample_comment):
    """GET /api/waywo-posts/{id} returns post with comments."""
    with (
        patch("src.routes.posts.get_post", return_value=sample_post),
        patch("src.routes.posts.get_comments_for_post", return_value=[sample_comment]),
    ):
        response = app_client.get("/api/waywo-posts/12345")

        assert response.status_code == 200
        data = response.json()
        assert data["post"]["id"] == 12345
        assert data["comment_count"] == 1
        assert data["comments"][0]["id"] == 111


@pytest.mark.route
def test_get_post_not_found(app_client):
    """GET /api/waywo-posts/{id} returns 404 for missing post."""
    with patch("src.routes.posts.get_post", return_value=None):
        response = app_client.get("/api/waywo-posts/99999")

        assert response.status_code == 404


@pytest.mark.route
def test_get_posts_chart_data(app_client, sample_post):
    """GET /api/waywo-posts/chart-data returns chart data."""
    with (
        patch("src.routes.posts.get_all_post_ids", return_value=[12345]),
        patch("src.routes.posts.get_post", return_value=sample_post),
        patch("src.routes.posts.get_comment_count_for_post", return_value=5),
    ):
        response = app_client.get("/api/waywo-posts/chart-data")

        assert response.status_code == 200
        data = response.json()
        assert data["total_posts"] == 1
        assert data["posts"][0]["comment_count"] == 5
        assert data["posts"][0]["label"] == "12/25"


@pytest.mark.route
def test_trigger_process_posts(app_client, mock_celery_result):
    """POST /api/process-waywo-posts enqueues post processing."""
    with patch("src.routes.posts.process_waywo_posts") as mock_task:
        mock_task.delay.return_value = mock_celery_result

        response = app_client.post("/api/process-waywo-posts")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "task_queued"
        assert data["task_id"] == "test-task-id-12345"


@pytest.mark.route
def test_trigger_process_comments(app_client, mock_celery_result):
    """POST /api/process-waywo-comments enqueues comment processing."""
    with patch("src.routes.posts.process_waywo_comments") as mock_task:
        mock_task.delay.return_value = mock_celery_result

        response = app_client.post("/api/process-waywo-comments")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "task_queued"
