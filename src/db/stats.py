"""Admin stats and database management operations."""

from src.db.database import SessionLocal
from src.db.models import WaywoCommentDB, WaywoPostDB, WaywoProjectDB


def get_db_session():
    return SessionLocal()


def reset_all_data() -> dict[str, int]:
    """
    Delete all data from all tables.

    Returns counts of deleted records per table.
    """
    db = get_db_session()
    try:
        # Delete in order to respect foreign key constraints
        # Projects first (references comments)
        projects_deleted = db.query(WaywoProjectDB).delete()

        # Comments next (references posts)
        comments_deleted = db.query(WaywoCommentDB).delete()

        # Posts last
        posts_deleted = db.query(WaywoPostDB).delete()

        db.commit()

        return {
            "projects_deleted": projects_deleted,
            "comments_deleted": comments_deleted,
            "posts_deleted": posts_deleted,
        }
    finally:
        db.close()


def get_database_stats() -> dict[str, int]:
    """Get counts for all tables."""
    db = get_db_session()
    try:
        return {
            "posts_count": db.query(WaywoPostDB).count(),
            "comments_count": db.query(WaywoCommentDB).count(),
            "projects_count": db.query(WaywoProjectDB).count(),
            "processed_comments_count": db.query(WaywoCommentDB)
            .filter(WaywoCommentDB.processed == True)
            .count(),
            "valid_projects_count": db.query(WaywoProjectDB)
            .filter(WaywoProjectDB.is_valid_project == True)
            .count(),
            "projects_with_embeddings_count": db.query(WaywoProjectDB)
            .filter(WaywoProjectDB.description_embedding.isnot(None))
            .count(),
        }
    finally:
        db.close()
