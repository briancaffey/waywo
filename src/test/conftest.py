"""Shared test fixtures for the waywo test suite."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.models import WaywoComment, WaywoPost, WaywoProject, WaywoYamlEntry

# ---------------------------------------------------------------------------
# Celery contrib pytest plugin (provides celery_app, celery_worker fixtures)
# ---------------------------------------------------------------------------
pytest_plugins = ("celery.contrib.pytest",)


# ---------------------------------------------------------------------------
# Sample Pydantic model instances
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_post_data():
    """Raw HN post data dict."""
    return {
        "id": 12345,
        "type": "story",
        "by": "testuser",
        "time": 1700000000,
        "title": "What are you working on? (December 2025)",
        "text": "Share what you're working on!",
        "score": 100,
        "descendants": 50,
        "kids": [111, 222, 333],
    }


@pytest.fixture
def sample_post(sample_post_data):
    """WaywoPost Pydantic model."""
    return WaywoPost(**sample_post_data, year=2025, month=12)


@pytest.fixture
def sample_comment_data():
    """Raw HN comment data dict."""
    return {
        "id": 111,
        "type": "comment",
        "by": "commenter1",
        "time": 1700000100,
        "text": "I'm working on a cool project! Check out https://example.com",
        "parent": 12345,
        "kids": [444, 555],
    }


@pytest.fixture
def sample_comment(sample_comment_data):
    """WaywoComment Pydantic model."""
    return WaywoComment(**sample_comment_data)


@pytest.fixture
def sample_project():
    """WaywoProject Pydantic model."""
    now = datetime.utcnow()
    return WaywoProject(
        id=1,
        source_comment_id=111,
        is_valid_project=True,
        title="Cool Project",
        short_description="A very cool project",
        description="This is a cool project that does amazing things.",
        hashtags=["python", "ai", "web"],
        project_urls=["https://example.com"],
        url_summaries={"https://example.com": "Example site"},
        primary_url="https://example.com",
        url_contents={},
        idea_score=8,
        complexity_score=5,
        created_at=now,
        processed_at=now,
        comment_time=1700000100,
        is_bookmarked=False,
        workflow_logs=["step1", "step2"],
    )


@pytest.fixture
def sample_project_2():
    """Second WaywoProject for list tests."""
    now = datetime.utcnow()
    return WaywoProject(
        id=2,
        source_comment_id=222,
        is_valid_project=True,
        title="Another Project",
        short_description="Another great project",
        description="This project is also great.",
        hashtags=["rust", "cli"],
        project_urls=["https://another.com"],
        url_summaries={},
        primary_url="https://another.com",
        url_contents={},
        idea_score=6,
        complexity_score=3,
        created_at=now,
        processed_at=now,
        comment_time=1700000200,
        is_bookmarked=True,
        workflow_logs=[],
    )


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------


@pytest.fixture
def app_client():
    """FastAPI TestClient with startup events mocked out.

    We patch init_db and init_tracing to avoid real DB/tracing initialization.
    We also patch the media directory creation to avoid filesystem side effects.
    """
    with (
        patch("src.main.init_db"),
        patch("src.main.init_tracing"),
        patch("src.main.os.makedirs"),
    ):
        from src.main import app

        with TestClient(app, raise_server_exceptions=False) as client:
            yield client


# ---------------------------------------------------------------------------
# Mock embedding helpers
# ---------------------------------------------------------------------------

FAKE_EMBEDDING_DIM = 4096


@pytest.fixture
def fake_embedding():
    """A fake embedding vector (4096-dim, all zeros except first few)."""
    emb = [0.0] * FAKE_EMBEDDING_DIM
    emb[0] = 1.0
    emb[1] = 0.5
    emb[2] = -0.3
    return emb


# ---------------------------------------------------------------------------
# Mock Celery task result
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_celery_result():
    """A mock Celery AsyncResult."""
    result = MagicMock()
    result.id = "test-task-id-12345"
    return result
