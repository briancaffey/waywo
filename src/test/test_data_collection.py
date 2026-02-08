"""Tests for Pydantic models and YAML loading."""

from io import StringIO
from unittest.mock import patch, mock_open

import pytest
import yaml

from src.models import WaywoComment, WaywoPost, WaywoYamlEntry
from src.worker.tasks import load_waywo_yaml

# Sample YAML content for testing load_waywo_yaml
SAMPLE_WAYWO_YAML = yaml.dump(
    [
        {"id": 12345, "year": 2025, "month": 12},
        {"id": 67890, "year": 2025, "month": 11},
    ]
)


def test_waywo_post_from_hn_data(sample_post_data):
    """Test creating WaywoPost from HN API data."""
    post = WaywoPost(**sample_post_data, year=2025, month=12)

    assert post.id == 12345
    assert post.type == "story"
    assert post.title == "What are you working on? (December 2025)"
    assert post.kids == [111, 222, 333]
    assert post.year == 2025
    assert post.month == 12


def test_waywo_comment_from_hn_data(sample_comment_data):
    """Test creating WaywoComment from HN API data."""
    comment = WaywoComment(**sample_comment_data)

    assert comment.id == 111
    assert comment.type == "comment"
    assert comment.by == "commenter1"
    assert comment.parent == 12345
    assert comment.kids == [444, 555]


def test_waywo_yaml_entry():
    """Test WaywoYamlEntry model."""
    entry = WaywoYamlEntry(id=12345, year=2025, month=12)

    assert entry.id == 12345
    assert entry.year == 2025
    assert entry.month == 12


def test_load_waywo_yaml():
    """Test that load_waywo_yaml parses YAML into WaywoYamlEntry models."""
    with patch("builtins.open", mock_open(read_data=SAMPLE_WAYWO_YAML)):
        entries = load_waywo_yaml()

    assert len(entries) == 2
    assert all(isinstance(e, WaywoYamlEntry) for e in entries)
    assert entries[0].id == 12345
    assert entries[0].year == 2025
    assert entries[1].id == 67890
