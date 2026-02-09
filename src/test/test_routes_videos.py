"""Tests for video route endpoints."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.models import WaywoVideo, WaywoVideoSegment


@pytest.fixture
def sample_video():
    """WaywoVideo Pydantic model."""
    now = datetime.utcnow()
    return WaywoVideo(
        id=1,
        project_id=1,
        version=1,
        video_title="Cool Project Video",
        video_style="dynamic",
        status="completed",
        view_count=5,
        is_favorited=False,
        created_at=now,
        width=1080,
        height=1920,
    )


@pytest.fixture
def sample_video_2():
    """Second WaywoVideo for list tests."""
    now = datetime.utcnow()
    return WaywoVideo(
        id=2,
        project_id=2,
        version=1,
        video_title="Another Video",
        video_style="calm",
        status="pending",
        view_count=0,
        is_favorited=True,
        created_at=now,
        width=1080,
        height=1920,
    )


@pytest.mark.route
def test_list_videos(app_client, sample_video):
    """GET /api/waywo-videos returns paginated videos."""
    with (
        patch("src.routes.videos.get_all_videos", return_value=[sample_video]),
        patch("src.routes.videos.get_video_count", return_value=1),
    ):
        response = app_client.get("/api/waywo-videos")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["videos"]) == 1
        assert data["videos"][0]["video_title"] == "Cool Project Video"


@pytest.mark.route
def test_list_videos_with_status(app_client, sample_video):
    """GET /api/waywo-videos?status=completed filters by status."""
    with (
        patch("src.routes.videos.get_all_videos", return_value=[sample_video]) as mock_get,
        patch("src.routes.videos.get_video_count", return_value=1),
    ):
        response = app_client.get("/api/waywo-videos?status=completed")

        assert response.status_code == 200
        mock_get.assert_called_once_with(limit=50, offset=0, status="completed")


@pytest.mark.route
def test_video_feed(app_client, sample_video):
    """GET /api/waywo-videos/feed returns completed videos only."""
    with (
        patch("src.routes.videos.get_video_feed", return_value=[sample_video]),
        patch("src.routes.videos.get_video_count", return_value=1),
    ):
        response = app_client.get("/api/waywo-videos/feed")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["videos"]) == 1


@pytest.mark.route
def test_get_video_detail(app_client, sample_video, sample_project):
    """GET /api/waywo-videos/{id} returns video with segments and project."""
    with (
        patch("src.routes.videos.get_video", return_value=sample_video),
        patch("src.routes.videos.get_project", return_value=sample_project),
    ):
        response = app_client.get("/api/waywo-videos/1")

        assert response.status_code == 200
        data = response.json()
        assert data["video"]["video_title"] == "Cool Project Video"
        assert data["project"]["title"] == "Cool Project"


@pytest.mark.route
def test_get_video_not_found(app_client):
    """GET /api/waywo-videos/{id} returns 404 for missing video."""
    with patch("src.routes.videos.get_video", return_value=None):
        response = app_client.get("/api/waywo-videos/99999")

        assert response.status_code == 404


@pytest.mark.route
def test_delete_video(app_client):
    """DELETE /api/waywo-videos/{id} deletes a video."""
    with patch("src.routes.videos.delete_video", return_value=True):
        response = app_client.delete("/api/waywo-videos/1")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"


@pytest.mark.route
def test_delete_video_not_found(app_client):
    """DELETE /api/waywo-videos/{id} returns 404 for missing video."""
    with patch("src.routes.videos.delete_video", return_value=False):
        response = app_client.delete("/api/waywo-videos/99999")

        assert response.status_code == 404


@pytest.mark.route
def test_toggle_favorite(app_client):
    """POST /api/waywo-videos/{id}/favorite toggles favorite."""
    with patch("src.routes.videos.toggle_video_favorite", return_value=True):
        response = app_client.post("/api/waywo-videos/1/favorite")

        assert response.status_code == 200
        data = response.json()
        assert data["is_favorited"] is True
        assert data["video_id"] == 1


@pytest.mark.route
def test_toggle_favorite_not_found(app_client):
    """POST /api/waywo-videos/{id}/favorite returns 404 for missing video."""
    with patch("src.routes.videos.toggle_video_favorite", return_value=None):
        response = app_client.post("/api/waywo-videos/99999/favorite")

        assert response.status_code == 404


@pytest.mark.route
def test_increment_view(app_client):
    """POST /api/waywo-videos/{id}/view increments view count."""
    with patch("src.routes.videos.increment_video_view_count", return_value=6):
        response = app_client.post("/api/waywo-videos/1/view")

        assert response.status_code == 200
        data = response.json()
        assert data["view_count"] == 6
        assert data["video_id"] == 1


@pytest.mark.route
def test_generate_video(app_client, sample_project, mock_celery_result):
    """POST /api/waywo-projects/{id}/generate-video triggers Celery task."""
    with (
        patch("src.routes.videos.get_project", return_value=sample_project),
        patch(
            "src.routes.videos.generate_video_task.delay",
            return_value=mock_celery_result,
        ),
    ):
        response = app_client.post("/api/waywo-projects/1/generate-video")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-id-12345"
        assert data["project_id"] == 1


@pytest.mark.route
def test_generate_video_project_not_found(app_client):
    """POST /api/waywo-projects/{id}/generate-video returns 404 for missing project."""
    with patch("src.routes.videos.get_project", return_value=None):
        response = app_client.post("/api/waywo-projects/99999/generate-video")

        assert response.status_code == 404


@pytest.mark.route
def test_list_project_videos(app_client, sample_video):
    """GET /api/waywo-projects/{id}/videos returns videos for project."""
    with patch("src.routes.videos.get_videos_for_project", return_value=[sample_video]):
        response = app_client.get("/api/waywo-projects/1/videos")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["project_id"] == 1
        assert len(data["videos"]) == 1


# ---------------------------------------------------------------------------
# Segment editing routes
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_segment():
    """WaywoVideoSegment Pydantic model."""
    now = datetime.utcnow()
    return WaywoVideoSegment(
        id=10,
        video_id=1,
        segment_index=0,
        segment_type="hook",
        narration_text="Original narration",
        scene_description="A cool scene",
        image_prompt="A cool image prompt",
        visual_style="abstract",
        transition="fade",
        status="complete",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.route
def test_update_segment_narration(app_client, sample_segment):
    """PATCH /api/waywo-videos/segments/{id}/narration updates narration."""
    updated = sample_segment.model_copy(update={"narration_text": "New narration", "status": "pending"})
    with (
        patch("src.routes.videos.get_segment", side_effect=[sample_segment, updated]),
        patch("src.routes.videos.update_segment_narration", return_value=True),
    ):
        response = app_client.patch(
            "/api/waywo-videos/segments/10/narration",
            json={"narration_text": "New narration"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["segment"]["narration_text"] == "New narration"
        assert "message" in data


@pytest.mark.route
def test_update_segment_narration_not_found(app_client):
    """PATCH /api/waywo-videos/segments/{id}/narration returns 404 for missing segment."""
    with patch("src.routes.videos.get_segment", return_value=None):
        response = app_client.patch(
            "/api/waywo-videos/segments/99999/narration",
            json={"narration_text": "New narration"},
        )

        assert response.status_code == 404


@pytest.mark.route
def test_update_segment_narration_missing_body(app_client):
    """PATCH /api/waywo-videos/segments/{id}/narration returns 422 without body."""
    response = app_client.patch(
        "/api/waywo-videos/segments/10/narration",
        json={},
    )

    assert response.status_code == 422


@pytest.mark.route
def test_update_segment_image_prompt(app_client, sample_segment):
    """PATCH /api/waywo-videos/segments/{id}/image-prompt updates image prompt."""
    updated = sample_segment.model_copy(update={"image_prompt": "New prompt", "image_path": None})
    with (
        patch("src.routes.videos.get_segment", side_effect=[sample_segment, updated]),
        patch("src.routes.videos.update_segment_image_prompt", return_value=True),
    ):
        response = app_client.patch(
            "/api/waywo-videos/segments/10/image-prompt",
            json={"image_prompt": "New prompt"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["segment"]["image_prompt"] == "New prompt"
        assert "message" in data


@pytest.mark.route
def test_update_segment_image_prompt_not_found(app_client):
    """PATCH /api/waywo-videos/segments/{id}/image-prompt returns 404 for missing segment."""
    with patch("src.routes.videos.get_segment", return_value=None):
        response = app_client.patch(
            "/api/waywo-videos/segments/99999/image-prompt",
            json={"image_prompt": "New prompt"},
        )

        assert response.status_code == 404


@pytest.mark.route
def test_update_segment_image_prompt_missing_body(app_client):
    """PATCH /api/waywo-videos/segments/{id}/image-prompt returns 422 without body."""
    response = app_client.patch(
        "/api/waywo-videos/segments/10/image-prompt",
        json={},
    )

    assert response.status_code == 422
