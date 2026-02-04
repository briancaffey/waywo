#!/usr/bin/env python3
"""
Migration script to transfer data from Redis to SQLite.

Usage:
    python -m src.migrate_redis_to_sqlite

This script:
1. Connects to Redis and reads all posts and comments
2. Initializes the SQLite database
3. Transfers all data to SQLite
4. Verifies the migration by comparing counts
"""

import json
import os
import sys

import redis

from src.database import init_db
from src.db_client import (
    get_all_comment_ids,
    get_all_post_ids,
    save_comment,
    save_post,
)
from src.models import WaywoComment, WaywoPost

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_redis_client() -> redis.Redis:
    """Get Redis client."""
    return redis.from_url(REDIS_URL, decode_responses=True)


def migrate_posts(redis_client: redis.Redis) -> int:
    """Migrate all posts from Redis to SQLite."""
    print("📦 Migrating posts...")

    # Get all post keys from Redis
    post_keys = redis_client.keys("waywo:post:*")
    print(f"   Found {len(post_keys)} posts in Redis")

    migrated = 0
    for key in post_keys:
        try:
            data = redis_client.get(key)
            if data:
                post = WaywoPost.model_validate_json(data)
                save_post(post)
                migrated += 1
                print(f"   ✅ Migrated post {post.id}: {post.title}")
        except Exception as e:
            print(f"   ❌ Error migrating {key}: {e}")

    print(f"   Migrated {migrated}/{len(post_keys)} posts")
    return migrated


def migrate_comments(redis_client: redis.Redis) -> int:
    """Migrate all comments from Redis to SQLite."""
    print("💬 Migrating comments...")

    # Get all comment keys from Redis
    comment_keys = redis_client.keys("waywo:comment:*")
    print(f"   Found {len(comment_keys)} comments in Redis")

    migrated = 0
    errors = 0
    for i, key in enumerate(comment_keys):
        try:
            data = redis_client.get(key)
            if data:
                comment = WaywoComment.model_validate_json(data)
                save_comment(comment)
                migrated += 1

                # Progress indicator every 100 comments
                if (i + 1) % 100 == 0:
                    print(f"   ... migrated {i + 1}/{len(comment_keys)} comments")
        except Exception as e:
            errors += 1
            print(f"   ❌ Error migrating {key}: {e}")

    print(f"   Migrated {migrated}/{len(comment_keys)} comments ({errors} errors)")
    return migrated


def verify_migration(redis_client: redis.Redis) -> bool:
    """Verify the migration by comparing counts."""
    print("\n🔍 Verifying migration...")

    # Redis counts
    redis_post_count = len(redis_client.keys("waywo:post:*"))
    redis_comment_count = len(redis_client.keys("waywo:comment:*"))

    # SQLite counts
    sqlite_post_count = len(get_all_post_ids())
    sqlite_comment_count = len(get_all_comment_ids())

    print(f"   Posts:    Redis={redis_post_count}, SQLite={sqlite_post_count}")
    print(f"   Comments: Redis={redis_comment_count}, SQLite={sqlite_comment_count}")

    posts_match = redis_post_count == sqlite_post_count
    comments_match = redis_comment_count == sqlite_comment_count

    if posts_match and comments_match:
        print("   ✅ Migration verified successfully!")
        return True
    else:
        print("   ⚠️  Count mismatch detected!")
        return False


def main():
    """Run the migration."""
    print("=" * 60)
    print("🚀 Redis to SQLite Migration")
    print("=" * 60)

    # Check Redis connection
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        print(f"✅ Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        sys.exit(1)

    # Initialize SQLite database
    print("\n📦 Initializing SQLite database...")
    init_db()

    # Run migration
    print("\n" + "-" * 60)
    post_count = migrate_posts(redis_client)

    print("\n" + "-" * 60)
    comment_count = migrate_comments(redis_client)

    # Verify
    print("\n" + "-" * 60)
    success = verify_migration(redis_client)

    # Summary
    print("\n" + "=" * 60)
    if success:
        print("✨ Migration completed successfully!")
        print(f"   Total posts migrated: {post_count}")
        print(f"   Total comments migrated: {comment_count}")
    else:
        print("⚠️  Migration completed with issues. Please review the logs.")
        sys.exit(1)

    print("=" * 60)


if __name__ == "__main__":
    main()
