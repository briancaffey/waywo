"""Tests for database operations using in-memory SQLite."""

import json
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.db.database import Base
from src.db.models import WaywoCommentDB, WaywoPostDB, WaywoProjectDB
from src.models import WaywoComment, WaywoPost, WaywoProject

# ---------------------------------------------------------------------------
# In-memory SQLite test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine (no vector extension)."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a test session factory bound to the in-memory engine."""
    TestSession = sessionmaker(bind=test_engine)
    return TestSession


@pytest.fixture(autouse=True)
def patch_db_sessions(test_session):
    """Patch all DB module get_db_session calls to use the test session."""
    with (
        patch("src.db.posts.get_db_session", test_session),
        patch("src.db.comments.get_db_session", test_session),
        patch("src.db.projects.get_db_session", test_session),
        patch("src.db.stats.get_db_session", test_session),
        patch("src.db.search.get_db_session", test_session),
    ):
        yield


# ---------------------------------------------------------------------------
# Post tests
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_save_and_get_post(sample_post):
    """save_post stores and get_post retrieves a post."""
    from src.db.posts import save_post, get_post

    save_post(sample_post)
    result = get_post(12345)

    assert result is not None
    assert result.id == 12345
    assert result.title == "What are you working on? (December 2025)"
    assert result.year == 2025
    assert result.month == 12
    assert result.kids == [111, 222, 333]


@pytest.mark.db
def test_save_post_update(sample_post):
    """save_post updates existing post."""
    from src.db.posts import save_post, get_post

    save_post(sample_post)

    # Update the post
    sample_post.score = 200
    save_post(sample_post)

    result = get_post(12345)
    assert result.score == 200


@pytest.mark.db
def test_get_post_not_found():
    """get_post returns None for non-existent post."""
    from src.db.posts import get_post

    result = get_post(99999)
    assert result is None


@pytest.mark.db
def test_get_all_post_ids(sample_post):
    """get_all_post_ids returns list of post IDs."""
    from src.db.posts import save_post, get_all_post_ids

    save_post(sample_post)
    ids = get_all_post_ids()

    assert 12345 in ids


# ---------------------------------------------------------------------------
# Comment tests
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_save_and_get_comment(sample_post, sample_comment):
    """save_comment stores and get_comment retrieves a comment."""
    from src.db.posts import save_post
    from src.db.comments import save_comment, get_comment

    # Must save parent post first (FK constraint)
    save_post(sample_post)
    save_comment(sample_comment)

    result = get_comment(111)
    assert result is not None
    assert result.id == 111
    assert result.by == "commenter1"
    assert result.parent == 12345


@pytest.mark.db
def test_comment_exists(sample_post, sample_comment):
    """comment_exists returns True for existing comments."""
    from src.db.posts import save_post
    from src.db.comments import save_comment, comment_exists

    save_post(sample_post)
    save_comment(sample_comment)

    assert comment_exists(111) is True
    assert comment_exists(99999) is False


@pytest.mark.db
def test_get_unprocessed_comments(sample_post, sample_comment):
    """get_unprocessed_comments returns unprocessed comments."""
    from src.db.posts import save_post
    from src.db.comments import save_comment, get_unprocessed_comments

    save_post(sample_post)
    save_comment(sample_comment)

    unprocessed = get_unprocessed_comments(limit=10)
    assert len(unprocessed) == 1
    assert unprocessed[0].id == 111


@pytest.mark.db
def test_mark_comment_processed(sample_post, sample_comment):
    """mark_comment_processed updates processed flag and timestamp."""
    from src.db.posts import save_post
    from src.db.comments import (
        save_comment,
        mark_comment_processed,
        is_comment_processed,
        get_unprocessed_comments,
    )

    save_post(sample_post)
    save_comment(sample_comment)

    assert is_comment_processed(111) is False

    mark_comment_processed(111)

    assert is_comment_processed(111) is True
    assert len(get_unprocessed_comments()) == 0


@pytest.mark.db
def test_get_all_comments(sample_post, sample_comment):
    """get_all_comments returns paginated comments."""
    from src.db.posts import save_post
    from src.db.comments import save_comment, get_all_comments, get_total_comment_count

    save_post(sample_post)
    save_comment(sample_comment)

    comments = get_all_comments(limit=10, offset=0)
    assert len(comments) == 1

    count = get_total_comment_count()
    assert count == 1


@pytest.mark.db
def test_get_comments_for_post(sample_post, sample_comment):
    """get_comments_for_post returns comments linked to a post."""
    from src.db.posts import save_post
    from src.db.comments import save_comment, get_comments_for_post

    save_post(sample_post)
    save_comment(sample_comment)

    comments = get_comments_for_post(12345)
    assert len(comments) == 1
    assert comments[0].id == 111


# ---------------------------------------------------------------------------
# Project tests
# ---------------------------------------------------------------------------


def _make_project(source_comment_id=111, **overrides):
    """Helper to create a WaywoProject."""
    now = datetime.utcnow()
    defaults = dict(
        id=0,
        source_comment_id=source_comment_id,
        is_valid_project=True,
        title="Test Project",
        short_description="Short desc",
        description="Long description here.",
        hashtags=["python", "web"],
        project_urls=["https://example.com"],
        url_summaries={},
        primary_url="https://example.com",
        url_contents={},
        idea_score=7,
        complexity_score=4,
        created_at=now,
        processed_at=now,
        workflow_logs=[],
    )
    defaults.update(overrides)
    return WaywoProject(**defaults)


@pytest.mark.db
def test_save_and_get_project(sample_post, sample_comment):
    """save_project stores and get_project retrieves a project."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project, get_project

    save_post(sample_post)
    save_comment(sample_comment)

    project = _make_project()
    project_id = save_project(project)

    assert project_id is not None
    assert project_id > 0

    result = get_project(project_id)
    assert result is not None
    assert result.title == "Test Project"
    assert result.hashtags == ["python", "web"]
    assert result.idea_score == 7


@pytest.mark.db
def test_save_project_with_embedding(sample_post, sample_comment):
    """save_project stores embedding blob."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project

    save_post(sample_post)
    save_comment(sample_comment)

    project = _make_project()
    embedding = [0.1, 0.2, 0.3, 0.4]
    project_id = save_project(project, embedding=embedding)

    assert project_id > 0


@pytest.mark.db
def test_delete_project(sample_post, sample_comment):
    """delete_project removes a project by ID."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project, delete_project, get_project

    save_post(sample_post)
    save_comment(sample_comment)

    project = _make_project()
    project_id = save_project(project)

    assert delete_project(project_id) is True
    assert get_project(project_id) is None
    assert delete_project(99999) is False


@pytest.mark.db
def test_toggle_bookmark(sample_post, sample_comment):
    """toggle_bookmark flips bookmark status."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project, toggle_bookmark

    save_post(sample_post)
    save_comment(sample_comment)

    project = _make_project()
    project_id = save_project(project)

    # Initially not bookmarked
    result = toggle_bookmark(project_id)
    assert result is True

    # Toggle back
    result = toggle_bookmark(project_id)
    assert result is False

    # Non-existent project
    assert toggle_bookmark(99999) is None


@pytest.mark.db
def test_get_all_projects(sample_post, sample_comment):
    """get_all_projects returns filtered project list."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project, get_all_projects, get_total_project_count

    save_post(sample_post)
    save_comment(sample_comment)

    save_project(_make_project(idea_score=8, complexity_score=3))
    save_project(_make_project(idea_score=4, complexity_score=7))

    # No filters
    all_projects = get_all_projects()
    assert len(all_projects) == 2

    # Filter by idea score
    filtered = get_all_projects(min_idea_score=6)
    assert len(filtered) == 1

    # Count
    assert get_total_project_count() == 2


@pytest.mark.db
def test_get_all_hashtags(sample_post, sample_comment):
    """get_all_hashtags returns deduplicated sorted tags."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project, get_all_hashtags

    save_post(sample_post)
    save_comment(sample_comment)

    save_project(_make_project(hashtags=["python", "web"]))
    save_project(_make_project(hashtags=["python", "ai"]))

    tags = get_all_hashtags()
    assert "python" in tags
    assert "web" in tags
    assert "ai" in tags
    # Should be deduplicated
    assert tags.count("python") == 1


@pytest.mark.db
def test_get_bookmarked_count(sample_post, sample_comment):
    """get_bookmarked_count returns number of bookmarked projects."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project, toggle_bookmark, get_bookmarked_count

    save_post(sample_post)
    save_comment(sample_comment)

    pid1 = save_project(_make_project())
    save_project(_make_project())

    assert get_bookmarked_count() == 0

    toggle_bookmark(pid1)
    assert get_bookmarked_count() == 1


# ---------------------------------------------------------------------------
# Stats tests
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_get_database_stats(sample_post, sample_comment):
    """get_database_stats returns correct counts."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project
    from src.db.stats import get_database_stats

    save_post(sample_post)
    save_comment(sample_comment)
    save_project(_make_project())

    stats = get_database_stats()
    assert stats["posts_count"] == 1
    assert stats["comments_count"] == 1
    assert stats["projects_count"] == 1


@pytest.mark.db
def test_reset_all_data(sample_post, sample_comment):
    """reset_all_data deletes all records."""
    from src.db.posts import save_post, get_all_post_ids
    from src.db.comments import save_comment
    from src.db.projects import save_project
    from src.db.stats import reset_all_data

    save_post(sample_post)
    save_comment(sample_comment)
    save_project(_make_project())

    result = reset_all_data()
    assert result["posts_deleted"] == 1
    assert result["comments_deleted"] == 1
    assert result["projects_deleted"] == 1

    assert get_all_post_ids() == []
