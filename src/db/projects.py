"""Project CRUD operations."""

import json
import logging
from datetime import datetime
from typing import Optional

import numpy as np
from sqlalchemy import func, or_

from src.db.database import SessionLocal
from src.clients.embedding import embedding_to_blob
from src.db.models import WaywoCommentDB, WaywoProjectDB
from src.models import WaywoProject

logger = logging.getLogger(__name__)


def get_db_session():
    return SessionLocal()


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
            source=project.source,
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
            primary_url=project.primary_url,
            url_contents=(
                json.dumps(project.url_contents) if project.url_contents else None
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
            .outerjoin(
                WaywoCommentDB, WaywoProjectDB.source_comment_id == WaywoCommentDB.id
            )
            .filter(WaywoProjectDB.id == project_id)
            .first()
        )
        if result is None:
            return None

        db_project, comment_time = result

        return WaywoProject(
            id=db_project.id,
            source_comment_id=db_project.source_comment_id,
            source=db_project.source,
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
            primary_url=db_project.primary_url,
            url_contents=(
                json.loads(db_project.url_contents) if db_project.url_contents else {}
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
            .outerjoin(
                WaywoCommentDB, WaywoProjectDB.source_comment_id == WaywoCommentDB.id
            )
            .filter(WaywoProjectDB.source_comment_id == comment_id)
            .all()
        )

        return [
            WaywoProject(
                id=p.id,
                source_comment_id=p.source_comment_id,
                source=p.source,
                is_valid_project=p.is_valid_project,
                invalid_reason=p.invalid_reason,
                title=p.title,
                short_description=p.short_description,
                description=p.description,
                hashtags=json.loads(p.hashtags) if p.hashtags else [],
                project_urls=json.loads(p.project_urls) if p.project_urls else [],
                url_summaries=json.loads(p.url_summaries) if p.url_summaries else {},
                primary_url=p.primary_url,
                url_contents=json.loads(p.url_contents) if p.url_contents else {},
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
    source: str | None = None,
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

        if source is not None:
            query = query.filter(WaywoProjectDB.source == source)

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
                source=p.source,
                is_valid_project=p.is_valid_project,
                invalid_reason=p.invalid_reason,
                title=p.title,
                short_description=p.short_description,
                description=p.description,
                hashtags=json.loads(p.hashtags) if p.hashtags else [],
                project_urls=json.loads(p.project_urls) if p.project_urls else [],
                url_summaries=json.loads(p.url_summaries) if p.url_summaries else {},
                primary_url=p.primary_url,
                url_contents=json.loads(p.url_contents) if p.url_contents else {},
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


def get_hashtag_counts(
    source: str | None = None,
    min_count: int = 1,
    limit: int = 200,
) -> dict:
    """Get hashtag frequency counts across all valid projects.

    Returns dict with 'tags' list (sorted by count desc), 'total_unique', and 'total_usage'.
    """
    db = get_db_session()
    try:
        query = db.query(WaywoProjectDB.hashtags).filter(
            WaywoProjectDB.is_valid_project == True,
        )
        if source is not None:
            query = query.filter(WaywoProjectDB.source == source)

        rows = query.all()

        counts: dict[str, int] = {}
        for (hashtags_json,) in rows:
            if hashtags_json:
                for tag in json.loads(hashtags_json):
                    counts[tag] = counts.get(tag, 0) + 1

        total_unique = len(counts)
        total_usage = sum(counts.values())

        # Filter by min_count, sort by count desc, apply limit
        tags = [
            {"tag": tag, "count": count}
            for tag, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)
            if count >= min_count
        ]
        if limit:
            tags = tags[:limit]

        return {
            "tags": tags,
            "total_unique": total_unique,
            "total_usage": total_usage,
        }
    finally:
        db.close()


def get_cluster_map_data() -> list[dict]:
    """Get lightweight project data for the cluster map visualization."""
    db = get_db_session()
    try:
        results = (
            db.query(
                WaywoProjectDB.id,
                WaywoProjectDB.title,
                WaywoProjectDB.short_description,
                WaywoProjectDB.hashtags,
                WaywoProjectDB.idea_score,
                WaywoProjectDB.complexity_score,
                WaywoProjectDB.cluster_label,
                WaywoProjectDB.umap_x,
                WaywoProjectDB.umap_y,
            )
            .filter(
                WaywoProjectDB.is_valid_project == True,
                WaywoProjectDB.umap_x.isnot(None),
                WaywoProjectDB.umap_y.isnot(None),
            )
            .all()
        )

        return [
            {
                "id": r.id,
                "title": r.title,
                "short_description": r.short_description,
                "hashtags": json.loads(r.hashtags) if r.hashtags else [],
                "idea_score": r.idea_score,
                "complexity_score": r.complexity_score,
                "cluster_label": r.cluster_label,
                "umap_x": r.umap_x,
                "umap_y": r.umap_y,
            }
            for r in results
        ]
    finally:
        db.close()


def compute_umap_clusters() -> int:
    """Run UMAP + HDBSCAN on all valid projects with embeddings.

    Writes umap_x, umap_y, cluster_label back to each project row.
    Returns the number of projects updated.
    """
    import hdbscan
    import umap
    from sklearn.preprocessing import StandardScaler

    db = get_db_session()
    try:
        rows = (
            db.query(WaywoProjectDB.id, WaywoProjectDB.description_embedding)
            .filter(
                WaywoProjectDB.is_valid_project == True,
                WaywoProjectDB.description_embedding.isnot(None),
            )
            .all()
        )

        if not rows:
            logger.warning("No valid projects with embeddings found")
            return 0

        ids = []
        embeddings = []
        target_len = None

        for row_id, blob in rows:
            vec = np.frombuffer(blob, dtype="<f4")
            if target_len is None:
                target_len = len(vec)
            if len(vec) == target_len:
                ids.append(row_id)
                embeddings.append(vec)

        if not embeddings:
            return 0

        X = np.vstack(embeddings)
        logger.info(f"Running UMAP on {X.shape[0]} projects with dim={X.shape[1]}")

        # StandardScaler + UMAP (same params as notebook)
        X_scaled = StandardScaler(with_mean=True, with_std=True).fit_transform(X)

        reducer = umap.UMAP(
            n_components=2,
            n_neighbors=15,
            min_dist=0.1,
            metric="cosine",
            random_state=42,
        )
        umap_2d = reducer.fit_transform(X_scaled)

        # HDBSCAN clustering on 2D projection
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=10,
            min_samples=5,
            metric="euclidean",
            cluster_selection_method="eom",
        )
        labels = clusterer.fit_predict(umap_2d)

        # Write results back
        for i, project_id in enumerate(ids):
            db.query(WaywoProjectDB).filter(WaywoProjectDB.id == project_id).update(
                {
                    WaywoProjectDB.umap_x: float(umap_2d[i, 0]),
                    WaywoProjectDB.umap_y: float(umap_2d[i, 1]),
                    WaywoProjectDB.cluster_label: int(labels[i]),
                }
            )

        db.commit()
        logger.info(f"Updated {len(ids)} projects with UMAP coordinates and cluster labels")
        return len(ids)
    finally:
        db.close()
