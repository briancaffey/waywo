"""Post CRUD operations."""

import json
from datetime import datetime

from src.db.database import SessionLocal
from src.db.models import WaywoPostDB
from src.models import WaywoPost


def get_db_session():
    return SessionLocal()


def save_post(post: WaywoPost) -> None:
    """Save a WaywoPost to the database."""
    db = get_db_session()
    try:
        # Check if post exists
        existing = db.query(WaywoPostDB).filter(WaywoPostDB.id == post.id).first()

        if existing:
            # Update existing post
            existing.type = post.type
            existing.by = post.by
            existing.time = post.time
            existing.text = post.text
            existing.dead = post.dead
            existing.deleted = post.deleted
            existing.kids = json.dumps(post.kids) if post.kids else None
            existing.title = post.title
            existing.url = post.url
            existing.score = post.score
            existing.descendants = post.descendants
            existing.year = post.year
            existing.month = post.month
            existing.updated_at = datetime.utcnow()
        else:
            # Create new post
            db_post = WaywoPostDB(
                id=post.id,
                type=post.type,
                by=post.by,
                time=post.time,
                text=post.text,
                dead=post.dead,
                deleted=post.deleted,
                kids=json.dumps(post.kids) if post.kids else None,
                title=post.title,
                url=post.url,
                score=post.score,
                descendants=post.descendants,
                year=post.year,
                month=post.month,
            )
            db.add(db_post)

        db.commit()
    finally:
        db.close()


def get_post(post_id: int) -> WaywoPost | None:
    """Retrieve a WaywoPost from the database."""
    db = get_db_session()
    try:
        db_post = db.query(WaywoPostDB).filter(WaywoPostDB.id == post_id).first()
        if db_post is None:
            return None

        return WaywoPost(
            id=db_post.id,
            type=db_post.type,
            by=db_post.by,
            time=db_post.time,
            text=db_post.text,
            dead=db_post.dead,
            deleted=db_post.deleted,
            kids=json.loads(db_post.kids) if db_post.kids else None,
            title=db_post.title,
            url=db_post.url,
            score=db_post.score,
            descendants=db_post.descendants,
            year=db_post.year,
            month=db_post.month,
        )
    finally:
        db.close()


def get_all_post_ids() -> list[int]:
    """Get all stored WaywoPost IDs from the database."""
    db = get_db_session()
    try:
        posts = db.query(WaywoPostDB.id).all()
        return [p.id for p in posts]
    finally:
        db.close()
