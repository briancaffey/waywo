"""Tests for Celery worker tasks.

Per Celery testing docs, we mock external dependencies and call task
functions directly rather than using task_always_eager.
For bound tasks, use .run() to call the underlying function without
Celery's wrapper injecting self.
"""

from unittest.mock import patch, MagicMock, mock_open

import pytest
import yaml

from src.models import WaywoComment, WaywoYamlEntry

# Sample YAML for testing load_waywo_yaml
SAMPLE_WAYWO_YAML = yaml.dump(
    [
        {"id": 12345, "year": 2025, "month": 12},
        {"id": 67890, "year": 2025, "month": 11},
    ]
)


# ---------------------------------------------------------------------------
# load_waywo_yaml (pure function, no Celery involved)
# ---------------------------------------------------------------------------


@pytest.mark.worker
def test_load_waywo_yaml():
    """load_waywo_yaml parses waywo.yml correctly."""
    from src.worker.tasks import load_waywo_yaml

    with patch("builtins.open", mock_open(read_data=SAMPLE_WAYWO_YAML)):
        entries = load_waywo_yaml()

    assert len(entries) == 2
    assert all(isinstance(e, WaywoYamlEntry) for e in entries)
    assert entries[0].id == 12345


# ---------------------------------------------------------------------------
# process_waywo_post
# ---------------------------------------------------------------------------


@pytest.mark.worker
def test_process_waywo_post(sample_post_data, sample_comment_data):
    """process_waywo_post fetches and saves post + comments."""
    from src.worker.tasks import process_waywo_post

    with (
        patch("src.worker.tasks.fetch_item") as mock_fetch,
        patch("src.worker.tasks.save_post") as mock_save_post,
        patch("src.worker.tasks.save_comment") as mock_save_comment,
        patch("src.worker.tasks.comment_exists", return_value=False),
    ):
        # First call returns post, subsequent calls return comments
        mock_fetch.side_effect = [
            sample_post_data,
            sample_comment_data,
            {
                "id": 222,
                "type": "comment",
                "by": "user2",
                "time": 1700000200,
                "text": "another",
                "parent": 12345,
            },
            {
                "id": 333,
                "type": "comment",
                "by": "user3",
                "time": 1700000300,
                "text": "third",
                "parent": 12345,
            },
        ]

        result = process_waywo_post(
            post_id=12345, year=2025, month=12, limit_comments=3
        )

    assert result["status"] == "success"
    assert result["post_id"] == 12345
    assert result["comments_saved"] == 3
    mock_save_post.assert_called_once()
    assert mock_save_comment.call_count == 3


@pytest.mark.worker
def test_process_waywo_post_skips_existing_comments(
    sample_post_data, sample_comment_data
):
    """process_waywo_post skips comments that already exist in DB."""
    from src.worker.tasks import process_waywo_post

    with (
        patch("src.worker.tasks.fetch_item") as mock_fetch,
        patch("src.worker.tasks.save_post"),
        patch("src.worker.tasks.save_comment") as mock_save_comment,
        patch("src.worker.tasks.comment_exists", return_value=True),
    ):
        mock_fetch.return_value = sample_post_data

        result = process_waywo_post(post_id=12345, year=2025, month=12)

    assert result["status"] == "success"
    assert result["comments_skipped"] == 3
    mock_save_comment.assert_not_called()


@pytest.mark.worker
def test_process_waywo_post_not_found():
    """process_waywo_post handles missing post gracefully."""
    from src.worker.tasks import process_waywo_post

    with patch("src.worker.tasks.fetch_item", return_value=None):
        result = process_waywo_post(post_id=99999)

    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# process_waywo_posts
# ---------------------------------------------------------------------------


@pytest.mark.worker
def test_process_waywo_posts():
    """process_waywo_posts enqueues individual post processing tasks."""
    from src.worker.tasks import process_waywo_posts

    mock_entries = [
        WaywoYamlEntry(id=1001, year=2025, month=1),
        WaywoYamlEntry(id=1002, year=2025, month=2),
    ]

    mock_task_result = MagicMock()
    mock_task_result.id = "task-123"

    with (
        patch("src.worker.tasks.load_waywo_yaml", return_value=mock_entries),
        patch("src.worker.tasks.process_waywo_post") as mock_task,
    ):
        mock_task.delay.return_value = mock_task_result

        result = process_waywo_posts(limit_posts=2)

    assert result["status"] == "queued"
    assert result["posts_queued"] == 2
    assert mock_task.delay.call_count == 2


# ---------------------------------------------------------------------------
# process_waywo_comment (bound task with self.retry)
# Uses .run() to call the underlying function directly, bypassing
# Celery's task wrapper which auto-injects self.
# ---------------------------------------------------------------------------


@pytest.mark.worker
def test_process_waywo_comment():
    """process_waywo_comment runs workflow and saves valid projects."""
    from src.worker.tasks import process_waywo_comment

    comment = WaywoComment(
        id=111,
        type="comment",
        by="testuser",
        time=1700000100,
        text="Working on a cool project",
        parent=12345,
    )

    workflow_result = {
        "projects": [
            {
                "is_valid": True,
                "title": "Cool Project",
                "short_description": "A cool project",
                "description": "Building something cool.",
                "hashtags": ["python"],
                "urls": ["https://example.com"],
                "url_summaries": {},
                "primary_url": "https://example.com",
                "url_contents": {},
                "idea_score": 8,
                "complexity_score": 5,
                "embedding": [0.1, 0.2],
                "workflow_logs": [],
            }
        ],
        "logs": [],
    }

    with (
        patch("src.worker.tasks.get_comment", return_value=comment),
        patch("src.worker.tasks.delete_projects_for_comment", return_value=0),
        patch("src.worker.tasks.asyncio") as mock_asyncio,
        patch("src.worker.tasks.save_project", return_value=1),
        patch("src.worker.tasks.mark_comment_processed"),
        patch("src.worker.tasks.capture_screenshot"),
        patch("src.worker.tasks.save_screenshot_to_disk", return_value="path.jpg"),
        patch("src.worker.tasks.update_project_screenshot"),
    ):
        mock_asyncio.run.side_effect = [
            workflow_result,  # run_workflow_async result
            b"fake_image_bytes",  # capture_screenshot result
        ]

        # Use .run() to bypass Celery's bound-task self injection
        result = process_waywo_comment.run(comment_id=111)

    assert result["status"] == "success"
    assert result["comment_id"] == 111
    assert result["valid_projects"] == 1


@pytest.mark.worker
def test_process_waywo_comment_not_found():
    """process_waywo_comment handles missing comment."""
    from src.worker.tasks import process_waywo_comment

    with patch("src.worker.tasks.get_comment", return_value=None):
        result = process_waywo_comment.run(comment_id=99999)

    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


@pytest.mark.worker
def test_process_waywo_comment_skips_invalid():
    """process_waywo_comment skips invalid projects."""
    from src.worker.tasks import process_waywo_comment

    comment = WaywoComment(
        id=111,
        type="comment",
        by="testuser",
        time=1700000100,
        text="Just a comment",
        parent=12345,
    )

    workflow_result = {
        "projects": [
            {
                "is_valid": False,
                "invalid_reason": "Not a project",
            }
        ],
        "logs": [],
    }

    with (
        patch("src.worker.tasks.get_comment", return_value=comment),
        patch("src.worker.tasks.delete_projects_for_comment", return_value=0),
        patch("src.worker.tasks.asyncio") as mock_asyncio,
        patch("src.worker.tasks.save_project") as mock_save,
        patch("src.worker.tasks.mark_comment_processed"),
    ):
        mock_asyncio.run.return_value = workflow_result

        result = process_waywo_comment.run(comment_id=111)

    assert result["status"] == "success"
    assert result["invalid_skipped"] == 1
    assert result["valid_projects"] == 0
    mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# process_waywo_comments (batch dispatcher)
# ---------------------------------------------------------------------------


@pytest.mark.worker
def test_process_waywo_comments():
    """process_waywo_comments dispatches tasks for unprocessed comments."""
    from src.worker.tasks import process_waywo_comments

    comments = [
        WaywoComment(
            id=111, type="comment", by="user1", time=1700000100, text="p1", parent=12345
        ),
        WaywoComment(
            id=222, type="comment", by="user2", time=1700000200, text="p2", parent=12345
        ),
    ]

    mock_task_result = MagicMock()
    mock_task_result.id = "task-abc"

    with (
        patch("src.worker.tasks.get_unprocessed_comments", return_value=comments),
        patch("src.worker.tasks.process_waywo_comment") as mock_task,
    ):
        mock_task.delay.return_value = mock_task_result

        result = process_waywo_comments(limit=10)

    assert result["status"] == "queued"
    assert result["comments_queued"] == 2
    assert mock_task.delay.call_count == 2


@pytest.mark.worker
def test_process_waywo_comments_no_work():
    """process_waywo_comments handles no unprocessed comments."""
    from src.worker.tasks import process_waywo_comments

    with patch("src.worker.tasks.get_unprocessed_comments", return_value=[]):
        result = process_waywo_comments()

    assert result["status"] == "no_work"
    assert result["comments_queued"] == 0


@pytest.mark.worker
def test_process_waywo_comments_specific_ids():
    """process_waywo_comments processes specific comment IDs."""
    from src.worker.tasks import process_waywo_comments

    comment = WaywoComment(
        id=111,
        type="comment",
        by="user1",
        time=1700000100,
        text="project",
        parent=12345,
    )

    mock_task_result = MagicMock()
    mock_task_result.id = "task-xyz"

    with (
        patch("src.worker.tasks.get_comment", return_value=comment),
        patch("src.worker.tasks.process_waywo_comment") as mock_task,
    ):
        mock_task.delay.return_value = mock_task_result

        result = process_waywo_comments(comment_ids=[111])

    assert result["status"] == "queued"
    assert result["comments_queued"] == 1
