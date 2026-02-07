"""Semantic search and vector similarity operations."""

import logging

from sqlalchemy import text

from src.db.database import SessionLocal
from src.clients.embedding import embedding_to_blob
from src.db.models import WaywoProjectDB
from src.models import WaywoProject

logger = logging.getLogger(__name__)


def get_db_session():
    return SessionLocal()


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
    from src.db.projects import get_project

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
        logger.warning(f"Semantic search failed: {e}")
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
    from src.db.projects import get_project

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
        logger.warning(f"Similar projects search failed: {e}")
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
