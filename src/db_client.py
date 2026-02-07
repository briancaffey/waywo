"""
Database client for waywo using SQLAlchemy with SQLite.

This module provides functions for CRUD operations on posts, comments, and projects.
Function signatures are designed to be compatible with the previous redis_client.py.
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import Session

from src.database import SessionLocal, init_db
from src.embedding_client import embedding_to_blob
from src.db_models import WaywoCommentDB, WaywoPostDB, WaywoProjectDB
from src.models import WaywoComment, WaywoPost, WaywoProject


def get_db_session() -> Session:
    """Get a new database session."""
    return SessionLocal()


# ============================================================================
# Post Operations
# ============================================================================


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


# ============================================================================
# Comment Operations
# ============================================================================


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
    """Get comments that haven't been processed yet."""
    db = get_db_session()
    try:
        query = (
            db.query(WaywoCommentDB)
            .filter(WaywoCommentDB.processed == False)
            .order_by(WaywoCommentDB.id.asc())
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


# ============================================================================
# Project Operations
# ============================================================================


def save_project(project: WaywoProject, embedding: list[float] | None = None) -> int:
    """Save a WaywoProject to the database. Returns the project ID.

    Args:
        project: The WaywoProject to save
        embedding: Optional embedding vector (list of floats) for semantic search
    """
    db = get_db_session()
    try:
        # Convert embedding to blob if provided
        embedding_blob = embedding_to_blob(embedding) if embedding else None

        db_project = WaywoProjectDB(
            source_comment_id=project.source_comment_id,
            is_valid_project=project.is_valid_project,
            invalid_reason=project.invalid_reason,
            title=project.title,
            short_description=project.short_description,
            description=project.description,
            hashtags=json.dumps(project.hashtags),
            project_urls=(
                json.dumps(project.project_urls) if project.project_urls else None
            ),
            url_summaries=(
                json.dumps(project.url_summaries) if project.url_summaries else None
            ),
            idea_score=project.idea_score,
            complexity_score=project.complexity_score,
            workflow_logs=(
                json.dumps(project.workflow_logs) if project.workflow_logs else None
            ),
            description_embedding=embedding_blob,
            created_at=project.created_at,
            processed_at=project.processed_at,
            screenshot_path=project.screenshot_path,
        )
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project.id
    finally:
        db.close()


def get_project(project_id: int) -> WaywoProject | None:
    """Retrieve a WaywoProject from the database."""
    db = get_db_session()
    try:
        result = (
            db.query(WaywoProjectDB, WaywoCommentDB.time)
            .outerjoin(WaywoCommentDB, WaywoProjectDB.source_comment_id == WaywoCommentDB.id)
            .filter(WaywoProjectDB.id == project_id)
            .first()
        )
        if result is None:
            return None

        db_project, comment_time = result

        return WaywoProject(
            id=db_project.id,
            source_comment_id=db_project.source_comment_id,
            is_valid_project=db_project.is_valid_project,
            invalid_reason=db_project.invalid_reason,
            title=db_project.title,
            short_description=db_project.short_description,
            description=db_project.description,
            hashtags=json.loads(db_project.hashtags) if db_project.hashtags else [],
            project_urls=(
                json.loads(db_project.project_urls) if db_project.project_urls else []
            ),
            url_summaries=(
                json.loads(db_project.url_summaries) if db_project.url_summaries else {}
            ),
            idea_score=db_project.idea_score,
            complexity_score=db_project.complexity_score,
            workflow_logs=(
                json.loads(db_project.workflow_logs) if db_project.workflow_logs else []
            ),
            created_at=db_project.created_at,
            processed_at=db_project.processed_at,
            is_bookmarked=db_project.is_bookmarked,
            screenshot_path=db_project.screenshot_path,
            comment_time=comment_time,
        )
    finally:
        db.close()


def get_projects_for_comment(comment_id: int) -> list[WaywoProject]:
    """Get all projects extracted from a specific comment."""
    db = get_db_session()
    try:
        results = (
            db.query(WaywoProjectDB, WaywoCommentDB.time)
            .outerjoin(WaywoCommentDB, WaywoProjectDB.source_comment_id == WaywoCommentDB.id)
            .filter(WaywoProjectDB.source_comment_id == comment_id)
            .all()
        )

        return [
            WaywoProject(
                id=p.id,
                source_comment_id=p.source_comment_id,
                is_valid_project=p.is_valid_project,
                invalid_reason=p.invalid_reason,
                title=p.title,
                short_description=p.short_description,
                description=p.description,
                hashtags=json.loads(p.hashtags) if p.hashtags else [],
                project_urls=json.loads(p.project_urls) if p.project_urls else [],
                url_summaries=json.loads(p.url_summaries) if p.url_summaries else {},
                idea_score=p.idea_score,
                complexity_score=p.complexity_score,
                workflow_logs=json.loads(p.workflow_logs) if p.workflow_logs else [],
                created_at=p.created_at,
                processed_at=p.processed_at,
                is_bookmarked=p.is_bookmarked,
                screenshot_path=p.screenshot_path,
                comment_time=comment_time,
            )
            for p, comment_time in results
        ]
    finally:
        db.close()


def delete_projects_for_comment(comment_id: int) -> int:
    """Delete all projects for a comment. Returns count of deleted projects."""
    db = get_db_session()
    try:
        count = (
            db.query(WaywoProjectDB)
            .filter(WaywoProjectDB.source_comment_id == comment_id)
            .delete()
        )
        db.commit()
        return count
    finally:
        db.close()


def delete_project(project_id: int) -> bool:
    """Delete a single project by ID. Returns True if deleted, False if not found."""
    db = get_db_session()
    try:
        count = (
            db.query(WaywoProjectDB).filter(WaywoProjectDB.id == project_id).delete()
        )
        db.commit()
        return count > 0
    finally:
        db.close()


def toggle_bookmark(project_id: int) -> bool | None:
    """Toggle bookmark status for a project. Returns new status, or None if not found."""
    db = get_db_session()
    try:
        db_project = (
            db.query(WaywoProjectDB).filter(WaywoProjectDB.id == project_id).first()
        )
        if db_project is None:
            return None
        db_project.is_bookmarked = not db_project.is_bookmarked
        db.commit()
        return db_project.is_bookmarked
    finally:
        db.close()


def update_project_screenshot(project_id: int, screenshot_path: str) -> bool:
    """Update the screenshot_path for a project. Returns True if updated, False if not found."""
    db = get_db_session()
    try:
        db_project = (
            db.query(WaywoProjectDB).filter(WaywoProjectDB.id == project_id).first()
        )
        if db_project is None:
            return False
        db_project.screenshot_path = screenshot_path
        db.commit()
        return True
    finally:
        db.close()


def get_bookmarked_count() -> int:
    """Get count of bookmarked projects."""
    db = get_db_session()
    try:
        return (
            db.query(WaywoProjectDB)
            .filter(WaywoProjectDB.is_bookmarked == True)
            .count()
        )
    finally:
        db.close()


def get_all_projects(
    limit: int | None = None,
    offset: int = 0,
    tags: list[str] | None = None,
    min_idea_score: int | None = None,
    max_idea_score: int | None = None,
    min_complexity_score: int | None = None,
    max_complexity_score: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    is_valid: bool | None = None,
    is_bookmarked: bool | None = None,
    sort: str | None = None,
) -> list[WaywoProject]:
    """Get all projects with optional filtering."""
    db = get_db_session()
    try:
        query = db.query(WaywoProjectDB, WaywoCommentDB.time).outerjoin(
            WaywoCommentDB, WaywoProjectDB.source_comment_id == WaywoCommentDB.id
        )

        # Apply filters
        if is_valid is not None:
            query = query.filter(WaywoProjectDB.is_valid_project == is_valid)

        if min_idea_score is not None:
            query = query.filter(WaywoProjectDB.idea_score >= min_idea_score)

        if max_idea_score is not None:
            query = query.filter(WaywoProjectDB.idea_score <= max_idea_score)

        if min_complexity_score is not None:
            query = query.filter(
                WaywoProjectDB.complexity_score >= min_complexity_score
            )

        if max_complexity_score is not None:
            query = query.filter(
                WaywoProjectDB.complexity_score <= max_complexity_score
            )

        if date_from is not None:
            query = query.filter(WaywoProjectDB.created_at >= date_from)

        if date_to is not None:
            query = query.filter(WaywoProjectDB.created_at <= date_to)

        if is_bookmarked is not None:
            query = query.filter(WaywoProjectDB.is_bookmarked == is_bookmarked)

        # Tag filtering (search in JSON array)
        if tags:
            # SQLite JSON search - check if any tag is contained in hashtags
            tag_conditions = []
            for tag in tags:
                tag_conditions.append(WaywoProjectDB.hashtags.like(f'%"{tag}"%'))
            query = query.filter(or_(*tag_conditions))

        # Order and paginate
        if sort == "random":
            query = query.order_by(func.random())
        else:
            query = query.order_by(WaywoProjectDB.created_at.desc())

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        results = query.all()

        return [
            WaywoProject(
                id=p.id,
                source_comment_id=p.source_comment_id,
                is_valid_project=p.is_valid_project,
                invalid_reason=p.invalid_reason,
                title=p.title,
                short_description=p.short_description,
                description=p.description,
                hashtags=json.loads(p.hashtags) if p.hashtags else [],
                project_urls=json.loads(p.project_urls) if p.project_urls else [],
                url_summaries=json.loads(p.url_summaries) if p.url_summaries else {},
                idea_score=p.idea_score,
                complexity_score=p.complexity_score,
                workflow_logs=json.loads(p.workflow_logs) if p.workflow_logs else [],
                created_at=p.created_at,
                processed_at=p.processed_at,
                is_bookmarked=p.is_bookmarked,
                screenshot_path=p.screenshot_path,
                comment_time=comment_time,
            )
            for p, comment_time in results
        ]
    finally:
        db.close()


def get_total_project_count(is_valid: bool | None = None) -> int:
    """Get total count of projects, optionally filtered by validity."""
    db = get_db_session()
    try:
        query = db.query(WaywoProjectDB)
        if is_valid is not None:
            query = query.filter(WaywoProjectDB.is_valid_project == is_valid)
        return query.count()
    finally:
        db.close()


def get_all_hashtags() -> list[str]:
    """Get all unique hashtags used across projects."""
    db = get_db_session()
    try:
        projects = db.query(WaywoProjectDB.hashtags).all()
        all_tags = set()
        for (hashtags,) in projects:
            if hashtags:
                tags = json.loads(hashtags)
                all_tags.update(tags)
        return sorted(list(all_tags))
    finally:
        db.close()


# ============================================================================
# Semantic Search Operations
# ============================================================================


def semantic_search(
    query_embedding: list[float],
    limit: int = 10,
    is_valid: bool | None = True,
) -> list[tuple[WaywoProject, float]]:
    """
    Perform semantic search using vector similarity.

    Args:
        query_embedding: The embedding vector to search with
        limit: Maximum number of results to return
        is_valid: Filter by validity (default True for valid projects only)

    Returns:
        List of (WaywoProject, similarity_score) tuples, sorted by similarity
    """
    db = get_db_session()
    try:
        # Convert embedding to blob for query
        query_blob = embedding_to_blob(query_embedding)

        # Use sqlite-vector's vector_full_scan for brute-force similarity search
        # This doesn't require quantization and works reliably across connections
        # Uses cosine distance (configured in vector_init)
        # Lower distance = more similar
        #
        # We use vector_full_scan_stream with a subquery to apply filters,
        # since vector_full_scan doesn't support WHERE clauses directly
        if is_valid is not None:
            sql = text("""
                SELECT p.id, v.distance
                FROM waywo_projects AS p
                JOIN vector_full_scan('waywo_projects', 'description_embedding', :query, :limit) AS v
                ON p.id = v.rowid
                WHERE p.is_valid_project = :is_valid
                ORDER BY v.distance ASC
            """)
            result = db.execute(
                sql, {"query": query_blob, "limit": limit * 2, "is_valid": is_valid}
            )
        else:
            sql = text("""
                SELECT v.rowid AS id, v.distance
                FROM vector_full_scan('waywo_projects', 'description_embedding', :query, :limit) AS v
                ORDER BY v.distance ASC
            """)
            result = db.execute(sql, {"query": query_blob, "limit": limit})

        # Fetch projects and convert distances to similarity scores
        results = []
        for row in result:
            project_id, distance = row
            project = get_project(project_id)
            if project:
                # Convert cosine distance to similarity (1 - distance for normalized vectors)
                # Cosine distance ranges from 0 (identical) to 2 (opposite)
                similarity = 1.0 - (distance / 2.0)
                results.append((project, similarity))
                if len(results) >= limit:
                    break

        return results
    except Exception as e:
        # If vector search fails (e.g., not initialized), return empty
        import logging

        logging.getLogger(__name__).warning(f"Semantic search failed: {e}")
        return []
    finally:
        db.close()


def get_similar_projects(
    project_id: int,
    limit: int = 5,
    is_valid: bool | None = True,
) -> list[tuple[WaywoProject, float]]:
    """
    Find projects similar to the given project using vector similarity.

    Args:
        project_id: The project to find similar projects for
        limit: Maximum number of similar projects to return
        is_valid: Filter by validity (default True for valid projects only)

    Returns:
        List of (WaywoProject, similarity_score) tuples, sorted by similarity
    """
    db = get_db_session()
    try:
        # Get the source project's embedding
        db_project = (
            db.query(WaywoProjectDB).filter(WaywoProjectDB.id == project_id).first()
        )
        if db_project is None or db_project.description_embedding is None:
            return []

        # Use the project's own embedding as the query
        query_blob = db_project.description_embedding

        # Search for similar projects, excluding the source project
        # Fetch extra to account for filtering out the source project
        fetch_limit = limit + 1
        if is_valid is not None:
            sql = text("""
                SELECT p.id, v.distance
                FROM waywo_projects AS p
                JOIN vector_full_scan('waywo_projects', 'description_embedding', :query, :fetch_limit) AS v
                ON p.id = v.rowid
                WHERE p.is_valid_project = :is_valid AND p.id != :exclude_id
                ORDER BY v.distance ASC
            """)
            result = db.execute(
                sql,
                {
                    "query": query_blob,
                    "fetch_limit": fetch_limit * 2,
                    "is_valid": is_valid,
                    "exclude_id": project_id,
                },
            )
        else:
            sql = text("""
                SELECT p.id, v.distance
                FROM waywo_projects AS p
                JOIN vector_full_scan('waywo_projects', 'description_embedding', :query, :fetch_limit) AS v
                ON p.id = v.rowid
                WHERE p.id != :exclude_id
                ORDER BY v.distance ASC
            """)
            result = db.execute(
                sql,
                {
                    "query": query_blob,
                    "fetch_limit": fetch_limit * 2,
                    "exclude_id": project_id,
                },
            )

        results = []
        for row in result:
            pid, distance = row
            proj = get_project(pid)
            if proj:
                similarity = 1.0 - (distance / 2.0)
                results.append((proj, similarity))
                if len(results) >= limit:
                    break

        return results
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Similar projects search failed: {e}")
        return []
    finally:
        db.close()


def get_projects_with_embeddings_count() -> int:
    """Get count of projects that have embeddings."""
    db = get_db_session()
    try:
        count = (
            db.query(WaywoProjectDB)
            .filter(WaywoProjectDB.description_embedding.isnot(None))
            .count()
        )
        return count
    finally:
        db.close()


# ============================================================================
# Admin Operations
# ============================================================================


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
