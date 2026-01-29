import os
from pathlib import Path

import yaml

from src.celery_app import celery_app
from src.hn_client import fetch_item
from src.models import WaywoComment, WaywoPost, WaywoYamlEntry
from src.redis_client import comment_exists, save_comment, save_post


def load_waywo_yaml() -> list[WaywoYamlEntry]:
    """Load and parse the waywo.yml file."""
    yaml_path = Path(__file__).parent.parent / "waywo.yml"
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    return [WaywoYamlEntry(**entry) for entry in data]


@celery_app.task(name="process_waywo_posts")
def process_waywo_posts(
    limit_posts: int | None = None,
    limit_comments: int | None = None,
) -> dict:
    """
    Process all WaywoPost entries from waywo.yml.

    Args:
        limit_posts: Maximum number of posts to process (for testing).
        limit_comments: Maximum comments per post (passed to process_waywo_post).

    Returns:
        Summary of processing results.
    """
    entries = load_waywo_yaml()

    if limit_posts is not None:
        entries = entries[:limit_posts]

    task_ids = []
    for entry in entries:
        task = process_waywo_post.delay(
            post_id=entry.id,
            year=entry.year,
            month=entry.month,
            limit_comments=limit_comments,
        )
        task_ids.append(task.id)

    return {
        "status": "queued",
        "posts_queued": len(entries),
        "task_ids": task_ids,
    }


@celery_app.task(name="process_waywo_post")
def process_waywo_post(
    post_id: int,
    year: int | None = None,
    month: int | None = None,
    limit_comments: int | None = None,
) -> dict:
    """
    Process a single WaywoPost and its top-level comments.

    Args:
        post_id: The HN item ID for the post.
        year: The year of the post (from waywo.yml).
        month: The month of the post (from waywo.yml).
        limit_comments: Maximum number of comments to fetch (for testing).

    Returns:
        Summary of processing results.
    """
    post_data = fetch_item(post_id)
    if post_data is None:
        return {"status": "error", "message": f"Could not fetch post {post_id}"}

    post = WaywoPost(
        **post_data,
        year=year,
        month=month,
    )
    save_post(post)

    kids = post.kids or []
    if limit_comments is not None:
        kids = kids[:limit_comments]

    comments_saved = 0
    comments_skipped = 0
    for comment_id in kids:
        # Skip if comment already exists
        if comment_exists(comment_id):
            comments_skipped += 1
            continue

        comment_data = fetch_item(comment_id)
        if comment_data is None:
            continue

        comment = WaywoComment(**comment_data)
        save_comment(comment)
        comments_saved += 1

    return {
        "status": "success",
        "post_id": post_id,
        "title": post.title,
        "total_kids": len(post.kids) if post.kids else 0,
        "comments_saved": comments_saved,
        "comments_skipped": comments_skipped,
    }
