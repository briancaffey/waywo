import pytest
from unittest.mock import MagicMock, patch

import fakeredis


@pytest.fixture
def mock_redis():
    """Provide a fake Redis client for testing."""
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    with patch("src.redis_client.get_redis_client", return_value=fake_redis):
        yield fake_redis


@pytest.fixture
def sample_post_data():
    """Sample HN post data for testing."""
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
def sample_comment_data():
    """Sample HN comment data for testing."""
    return {
        "id": 111,
        "type": "comment",
        "by": "commenter1",
        "time": 1700000100,
        "text": "I'm working on a cool project!",
        "parent": 12345,
        "kids": [444, 555],
    }


@pytest.fixture
def mock_hn_api(sample_post_data, sample_comment_data):
    """Mock the HN API fetch_item function."""
    items = {
        12345: sample_post_data,
        111: sample_comment_data,
        222: {
            "id": 222,
            "type": "comment",
            "by": "commenter2",
            "time": 1700000200,
            "text": "Another project here",
            "parent": 12345,
        },
        333: {
            "id": 333,
            "type": "comment",
            "by": "commenter3",
            "time": 1700000300,
            "text": "My side project",
            "parent": 12345,
        },
    }

    def mock_fetch(item_id):
        return items.get(item_id)

    with patch("src.tasks.fetch_item", side_effect=mock_fetch):
        yield items
