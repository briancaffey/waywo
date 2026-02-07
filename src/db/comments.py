"""Comment CRUD operations."""

import json
from datetime import datetime

from sqlalchemy.sql.expression import func

from src.db.database import SessionLocal
from src.db.models import WaywoCommentDB
from src.models import WaywoComment


def get_db_session():
    return SessionLocal()


def save_comment(comment: WaywoComment) -> None:
    """Save a WaywoComment to the database."""
    db = get_db_session()
    try:
        # Check if comment exists
        existing = (
            db.query(WaywoCommentDB).filter(WaywoCommentDB.id == comment.id).first()
        )

        if existing:
            # Update existing comment
            existing.type = comment.type
            existing.by = comment.by
            existing.time = comment.time
            existing.text = comment.text
            existing.dead = comment.dead
            existing.deleted = comment.deleted
            existing.kids = json.dumps(comment.kids) if comment.kids else None
            existing.parent = comment.parent
            existing.updated_at = datetime.utcnow()
        else:
            # Create new comment
            db_comment = WaywoCommentDB(
                id=comment.id,
                type=comment.type,
                by=comment.by,
                time=comment.time,
                text=comment.text,
                dead=comment.dead,
                deleted=comment.deleted,
                kids=json.dumps(comment.kids) if comment.kids else None,
                parent=comment.parent,
            )
            db.add(db_comment)

        db.commit()
    finally:
        db.close()


def get_comment(comment_id: int) -> WaywoComment | None:
    """Retrieve a WaywoComment from the database."""
    db = get_db_session()
    try:
        db_comment = (
            db.query(WaywoCommentDB).filter(WaywoCommentDB.id == comment_id).first()
        )
        if db_comment is None:
            return None

        return WaywoComment(
            id=db_comment.id,
            type=db_comment.type,
            by=db_comment.by,
            time=db_comment.time,
            text=db_comment.text,
            dead=db_comment.dead,
            deleted=db_comment.deleted,
            kids=json.loads(db_comment.kids) if db_comment.kids else None,
            parent=db_comment.parent,
        )
    finally:
        db.close()


def comment_exists(comment_id: int) -> bool:
    """Check if a comment exists in the database."""
    db = get_db_session()
    try:
        count = db.query(WaywoCommentDB).filter(WaywoCommentDB.id == comment_id).count()
        return count > 0
    finally:
        db.close()


def get_all_comment_ids() -> list[int]:
    """Get all stored WaywoComment IDs from the database."""
    db = get_db_session()
    try:
        comments = db.query(WaywoCommentDB.id).all()
        return [c.id for c in comments]
    finally:
        db.close()


def get_comments_for_post(post_id: int) -> list[WaywoComment]:
    """Get all comments for a specific post."""
    from src.db.posts import get_post

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
    from src.db.posts import get_post

    post = get_post(post_id)
    if post is None or post.kids is None:
        return 0

    db = get_db_session()
    try:
        count = (
            db.query(WaywoCommentDB).filter(WaywoCommentDB.id.in_(post.kids)).count()
        )
        return count
    finally:
        db.close()


def get_all_comments(
    limit: int | None = None,
    offset: int = 0,
    post_id: int | None = None,
) -> list[WaywoComment]:
    """Get all stored comments with optional pagination and filtering."""
    db = get_db_session()
    try:
        query = db.query(WaywoCommentDB).order_by(WaywoCommentDB.id.desc())

        # Filter by parent post if specified
        if post_id is not None:
            query = query.filter(WaywoCommentDB.parent == post_id)

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        db_comments = query.all()

        return [
            WaywoComment(
                id=c.id,
                type=c.type,
                by=c.by,
                time=c.time,
                text=c.text,
                dead=c.dead,
                deleted=c.deleted,
                kids=json.loads(c.kids) if c.kids else None,
                parent=c.parent,
            )
            for c in db_comments
        ]
    finally:
        db.close()


def get_total_comment_count(post_id: int | None = None) -> int:
    """Get total count of stored comments, optionally filtered by post."""
    db = get_db_session()
    try:
        query = db.query(WaywoCommentDB)
        if post_id is not None:
            query = query.filter(WaywoCommentDB.parent == post_id)
        return query.count()
    finally:
        db.close()


def get_unprocessed_comments(limit: int | None = None) -> list[WaywoComment]:
    """Get comments that haven't been processed yet, in random order."""
    db = get_db_session()
    try:
        query = (
            db.query(WaywoCommentDB)
            .filter(WaywoCommentDB.processed == False)
            .order_by(func.random())
        )

        if limit:
            query = query.limit(limit)

        db_comments = query.all()

        return [
            WaywoComment(
                id=c.id,
                type=c.type,
                by=c.by,
                time=c.time,
                text=c.text,
                dead=c.dead,
                deleted=c.deleted,
                kids=json.loads(c.kids) if c.kids else None,
                parent=c.parent,
            )
            for c in db_comments
        ]
    finally:
        db.close()


def mark_comment_processed(comment_id: int) -> None:
    """Mark a comment as processed."""
    db = get_db_session()
    try:
        db_comment = (
            db.query(WaywoCommentDB).filter(WaywoCommentDB.id == comment_id).first()
        )
        if db_comment:
            db_comment.processed = True
            db_comment.processed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def is_comment_processed(comment_id: int) -> bool:
    """Check if a comment has been processed."""
    db = get_db_session()
    try:
        db_comment = (
            db.query(WaywoCommentDB).filter(WaywoCommentDB.id == comment_id).first()
        )
        return db_comment.processed if db_comment else False
    finally:
        db.close()
