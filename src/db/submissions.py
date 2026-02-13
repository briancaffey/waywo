"""Project submission CRUD and deduplication queries."""

import logging
from typing import Optional

from sqlalchemy import text

from src.db.database import SessionLocal
from src.db.models import (
    WaywoCommentDB,
    WaywoPostDB,
    WaywoProjectDB,
    WaywoProjectSubmissionDB,
)
from src.clients.embedding import embedding_to_blob
from src.models import WaywoProjectSubmission

logger = logging.getLogger(__name__)


def get_db_session():
    return SessionLocal()


def save_submission(
    project_id: int,
    comment_id: int,
    extracted_text: str | None = None,
    similarity_score: float | None = None,
) -> int:
    """Save a project submission record. Returns the submission ID."""
    db = get_db_session()
    try:
        submission = WaywoProjectSubmissionDB(
            project_id=project_id,
            comment_id=comment_id,
            extracted_text=extracted_text,
            similarity_score=similarity_score,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission.id
    finally:
        db.close()


def get_submissions_for_project(project_id: int) -> list[WaywoProjectSubmission]:
    """Get all submissions for a project, enriched with comment and post data."""
    db = get_db_session()
    try:
        results = (
            db.query(
                WaywoProjectSubmissionDB,
                WaywoCommentDB.by,
                WaywoCommentDB.time,
                WaywoCommentDB.parent,
                WaywoPostDB.title,
                WaywoPostDB.year,
                WaywoPostDB.month,
            )
            .join(
                WaywoCommentDB,
                WaywoProjectSubmissionDB.comment_id == WaywoCommentDB.id,
            )
            .outerjoin(WaywoPostDB, WaywoCommentDB.parent == WaywoPostDB.id)
            .filter(WaywoProjectSubmissionDB.project_id == project_id)
            .order_by(WaywoProjectSubmissionDB.created_at.asc())
            .all()
        )

        return [
            WaywoProjectSubmission(
                id=sub.id,
                project_id=sub.project_id,
                comment_id=sub.comment_id,
                extracted_text=sub.extracted_text,
                similarity_score=sub.similarity_score,
                created_at=sub.created_at,
                comment_by=comment_by,
                comment_time=comment_time,
                post_id=parent_post_id,
                post_title=post_title,
                year=year,
                month=month,
            )
            for sub, comment_by, comment_time, parent_post_id, post_title, year, month in results
        ]
    finally:
        db.close()


def get_submission_count(project_id: int) -> int:
    """Get the number of submissions for a project."""
    db = get_db_session()
    try:
        return (
            db.query(WaywoProjectSubmissionDB)
            .filter(WaywoProjectSubmissionDB.project_id == project_id)
            .count()
        )
    finally:
        db.close()


def find_duplicate_by_author(
    author: str,
    embedding: list[float],
    similarity_threshold: float = 0.85,
) -> Optional[tuple[int, float]]:
    """Find a duplicate project by the same author using vector similarity.

    Args:
        author: The HN username to check against.
        embedding: The preliminary embedding of the new project text.
        similarity_threshold: Minimum cosine similarity to consider a duplicate.

    Returns:
        Tuple of (project_id, similarity_score) if a duplicate is found, else None.
    """
    db = get_db_session()
    try:
        query_blob = embedding_to_blob(embedding)

        # Vector search filtered to projects by the same author.
        # We join through the source comment to get the author.
        sql = text("""
            SELECT p.id, v.distance
            FROM waywo_projects AS p
            JOIN vector_full_scan('waywo_projects', 'description_embedding', :query, :limit) AS v
                ON p.id = v.rowid
            JOIN waywo_comments AS c
                ON p.source_comment_id = c.id
            WHERE p.is_valid_project = 1
                AND c.by = :author
            ORDER BY v.distance ASC
            LIMIT 1
        """)

        result = db.execute(
            sql,
            {"query": query_blob, "limit": 100, "author": author},
        )

        row = result.fetchone()
        if row is None:
            return None

        project_id, distance = row
        # Convert cosine distance to similarity
        similarity = 1.0 - (distance / 2.0)

        if similarity >= similarity_threshold:
            return (project_id, similarity)

        return None
    except Exception as e:
        logger.warning(f"Duplicate check failed: {e}")
        return None
    finally:
        db.close()


def delete_submissions_for_comment(comment_id: int) -> int:
    """Delete all submissions linked to a specific comment. Returns count deleted."""
    db = get_db_session()
    try:
        count = (
            db.query(WaywoProjectSubmissionDB)
            .filter(WaywoProjectSubmissionDB.comment_id == comment_id)
            .delete()
        )
        db.commit()
        return count
    finally:
        db.close()
