import json
import os

import redis

from src.models import WaywoComment, WaywoPost

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Get or create a Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def get_post_key(post_id: int) -> str:
    """Generate Redis key for a WaywoPost."""
    return f"waywo:post:{post_id}"


def get_comment_key(comment_id: int) -> str:
    """Generate Redis key for a WaywoComment."""
    return f"waywo:comment:{comment_id}"


def save_post(post: WaywoPost) -> None:
    """Save a WaywoPost to Redis."""
    client = get_redis_client()
    key = get_post_key(post.id)
    client.set(key, post.model_dump_json())


def save_comment(comment: WaywoComment) -> None:
    """Save a WaywoComment to Redis."""
    client = get_redis_client()
    key = get_comment_key(comment.id)
    client.set(key, comment.model_dump_json())


def get_post(post_id: int) -> WaywoPost | None:
    """Retrieve a WaywoPost from Redis."""
    client = get_redis_client()
    key = get_post_key(post_id)
    data = client.get(key)
    if data is None:
        return None
    return WaywoPost.model_validate_json(data)


def get_comment(comment_id: int) -> WaywoComment | None:
    """Retrieve a WaywoComment from Redis."""
    client = get_redis_client()
    key = get_comment_key(comment_id)
    data = client.get(key)
    if data is None:
        return None
    return WaywoComment.model_validate_json(data)


def get_all_post_ids() -> list[int]:
    """Get all stored WaywoPost IDs from Redis."""
    client = get_redis_client()
    keys = client.keys("waywo:post:*")
    return [int(key.split(":")[-1]) for key in keys]


def get_comments_for_post(post_id: int) -> list[WaywoComment]:
    """Get all comments for a specific post."""
    post = get_post(post_id)
    if post is None or post.kids is None:
        return []

    comments = []
    for comment_id in post.kids:
        comment = get_comment(comment_id)
        if comment is not None:
            comments.append(comment)
    return comments


def get_comment_count_for_post(post_id: int) -> int:
    """Get count of stored comments for a post."""
    post = get_post(post_id)
    if post is None or post.kids is None:
        return 0

    client = get_redis_client()
    count = 0
    for comment_id in post.kids:
        key = get_comment_key(comment_id)
        if client.exists(key):
            count += 1
    return count


def comment_exists(comment_id: int) -> bool:
    """Check if a comment exists in Redis."""
    client = get_redis_client()
    key = get_comment_key(comment_id)
    return client.exists(key) > 0


def get_all_comment_ids() -> list[int]:
    """Get all stored WaywoComment IDs from Redis."""
    client = get_redis_client()
    keys = client.keys("waywo:comment:*")
    return [int(key.split(":")[-1]) for key in keys]


def get_all_comments(limit: int | None = None, offset: int = 0) -> list[WaywoComment]:
    """Get all stored comments with optional pagination."""
    comment_ids = get_all_comment_ids()
    comment_ids.sort(reverse=True)  # Sort by ID descending (newer first)

    if offset:
        comment_ids = comment_ids[offset:]
    if limit:
        comment_ids = comment_ids[:limit]

    comments = []
    for comment_id in comment_ids:
        comment = get_comment(comment_id)
        if comment is not None:
            comments.append(comment)
    return comments


def get_total_comment_count() -> int:
    """Get total count of stored comments."""
    client = get_redis_client()
    keys = client.keys("waywo:comment:*")
    return len(keys)
