import pytest
from unittest.mock import patch, MagicMock

from src.models import WaywoPost, WaywoComment, WaywoYamlEntry
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
