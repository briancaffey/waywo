import pytest
from unittest.mock import patch, MagicMock

from src.models import WaywoPost, WaywoComment, WaywoYamlEntry
from src.redis_client import (
    comment_exists,
    get_comment,
    get_comment_key,
    get_post,
    get_post_key,
    save_comment,
    save_post,
)
from src.tasks import process_waywo_post, load_waywo_yaml


class TestModels:
    """Tests for Pydantic models."""

    def test_waywo_post_from_hn_data(self, sample_post_data):
        """Test creating WaywoPost from HN API data."""
        post = WaywoPost(**sample_post_data, year=2025, month=12)

        assert post.id == 12345
        assert post.type == "story"
        assert post.title == "What are you working on? (December 2025)"
        assert post.kids == [111, 222, 333]
        assert post.year == 2025
        assert post.month == 12

    def test_waywo_comment_from_hn_data(self, sample_comment_data):
        """Test creating WaywoComment from HN API data."""
        comment = WaywoComment(**sample_comment_data)

        assert comment.id == 111
        assert comment.type == "comment"
        assert comment.by == "commenter1"
        assert comment.parent == 12345
        assert comment.kids == [444, 555]

    def test_waywo_yaml_entry(self):
        """Test WaywoYamlEntry model."""
        entry = WaywoYamlEntry(id=12345, year=2025, month=12)

        assert entry.id == 12345
        assert entry.year == 2025
        assert entry.month == 12


class TestRedisClient:
    """Tests for Redis client operations."""

    def test_get_post_key(self):
        """Test post key generation."""
        assert get_post_key(12345) == "waywo:post:12345"

    def test_get_comment_key(self):
        """Test comment key generation."""
        assert get_comment_key(111) == "waywo:comment:111"

    def test_save_and_get_post(self, mock_redis, sample_post_data):
        """Test saving and retrieving a post."""
        post = WaywoPost(**sample_post_data, year=2025, month=12)
        save_post(post)

        retrieved = get_post(12345)
        assert retrieved is not None
        assert retrieved.id == post.id
        assert retrieved.title == post.title
        assert retrieved.year == 2025

    def test_save_and_get_comment(self, mock_redis, sample_comment_data):
        """Test saving and retrieving a comment."""
        comment = WaywoComment(**sample_comment_data)
        save_comment(comment)

        retrieved = get_comment(111)
        assert retrieved is not None
        assert retrieved.id == comment.id
        assert retrieved.by == comment.by

    def test_get_nonexistent_post(self, mock_redis):
        """Test retrieving a post that doesn't exist."""
        result = get_post(99999)
        assert result is None


class TestTasks:
    """Tests for Celery tasks."""

    def test_process_waywo_post_success(self, mock_redis, mock_hn_api):
        """Test processing a single post successfully."""
        result = process_waywo_post(
            post_id=12345,
            year=2025,
            month=12,
            limit_comments=None,
        )

        assert result["status"] == "success"
        assert result["post_id"] == 12345
        assert result["comments_saved"] == 3
        assert result["comments_skipped"] == 0

        # Verify post was saved
        post = get_post(12345)
        assert post is not None
        assert post.year == 2025

        # Verify comments were saved
        comment = get_comment(111)
        assert comment is not None
        assert comment.by == "commenter1"

    def test_process_waywo_post_with_limit(self, mock_redis, mock_hn_api):
        """Test processing a post with comment limit."""
        result = process_waywo_post(
            post_id=12345,
            year=2025,
            month=12,
            limit_comments=2,
        )

        assert result["status"] == "success"
        assert result["comments_saved"] == 2

    def test_process_waywo_post_skips_existing(self, mock_redis, mock_hn_api):
        """Test that existing comments are skipped."""
        # First, save one comment directly
        comment = WaywoComment(
            id=111, type="comment", by="existing", time=1700000000, parent=12345
        )
        save_comment(comment)
        assert comment_exists(111)

        # Now process the post - comment 111 should be skipped
        result = process_waywo_post(
            post_id=12345,
            year=2025,
            month=12,
            limit_comments=None,
        )

        assert result["status"] == "success"
        assert result["comments_saved"] == 2  # Only 222 and 333
        assert result["comments_skipped"] == 1  # Comment 111 was skipped

        # Verify the existing comment wasn't overwritten
        existing = get_comment(111)
        assert existing.by == "existing"  # Original value, not "commenter1"

    def test_process_waywo_post_not_found(self, mock_redis):
        """Test processing a post that doesn't exist."""
        with patch("src.tasks.fetch_item", return_value=None):
            result = process_waywo_post(post_id=99999, year=2025, month=1)

        assert result["status"] == "error"
        assert "Could not fetch" in result["message"]


class TestLoadWaywoYaml:
    """Tests for loading waywo.yml."""

    def test_load_waywo_yaml(self):
        """Test that waywo.yml loads correctly."""
        entries = load_waywo_yaml()

        assert len(entries) > 0
        assert all(isinstance(e, WaywoYamlEntry) for e in entries)
        assert all(
            hasattr(e, "id") and hasattr(e, "year") and hasattr(e, "month")
            for e in entries
        )
