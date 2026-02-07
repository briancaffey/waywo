from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.db.client import (
    delete_project,
    get_all_hashtags,
    get_all_projects,
    get_bookmarked_count,
    get_comment,
    get_post,
    get_project,
    get_projects_for_comment,
    get_similar_projects,
    get_total_project_count,
    toggle_bookmark,
)

router = APIRouter()


@router.get("/api/waywo-projects", tags=["projects"])
async def list_waywo_projects(
    limit: int = 50,
    offset: int = 0,
    comment_id: Optional[int] = None,
    tags: Optional[str] = Query(None, description="Comma-separated list of tags"),
    min_idea_score: Optional[int] = Query(None, ge=1, le=10),
    max_idea_score: Optional[int] = Query(None, ge=1, le=10),
    min_complexity_score: Optional[int] = Query(None, ge=1, le=10),
    max_complexity_score: Optional[int] = Query(None, ge=1, le=10),
    is_valid: Optional[bool] = None,
    bookmarked: Optional[bool] = Query(None, description="Filter by bookmark status"),
    date_from: Optional[datetime] = Query(
        None, description="Filter projects created on or after this date (ISO format)"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Filter projects created on or before this date (ISO format)"
    ),
    sort: Optional[str] = Query(
        None,
        description="Sort order: 'random' for random order, default is newest first",
    ),
):
    """
    List all WaywoProject entries with pagination and filtering.

    Filters:
    - comment_id: Filter by source comment
    - tags: Comma-separated list of hashtags to filter by
    - min/max_idea_score: Filter by idea score range
    - min/max_complexity_score: Filter by complexity score range
    - is_valid: Filter by validity status
    - bookmarked: Filter by bookmark status (true/false)
    - date_from/date_to: Filter by creation date range (ISO format)
    """
    # Parse tags if provided
    tag_list = None
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]

    # If filtering by comment_id, use the dedicated function
    if comment_id is not None:
        projects = get_projects_for_comment(comment_id)
        total = len(projects)
    else:
        projects = get_all_projects(
            limit=limit,
            offset=offset,
            tags=tag_list,
            min_idea_score=min_idea_score,
            max_idea_score=max_idea_score,
            min_complexity_score=min_complexity_score,
            max_complexity_score=max_complexity_score,
            is_valid=is_valid,
            is_bookmarked=bookmarked,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
        )
        total = get_total_project_count(is_valid=is_valid)

    # Get bookmarked count for the response
    bookmarked_count = get_bookmarked_count()

    return {
        "projects": [p.model_dump() for p in projects],
        "total": total,
        "bookmarked_count": bookmarked_count,
        "limit": limit,
        "offset": offset,
        "filters": {
            "comment_id": comment_id,
            "tags": tag_list,
            "min_idea_score": min_idea_score,
            "max_idea_score": max_idea_score,
            "min_complexity_score": min_complexity_score,
            "max_complexity_score": max_complexity_score,
            "is_valid": is_valid,
            "bookmarked": bookmarked,
        },
    }


@router.get("/api/waywo-projects/hashtags", tags=["projects"])
async def list_project_hashtags():
    """
    Get all unique hashtags used across projects.

    Useful for tag autocomplete/filtering.
    """
    hashtags = get_all_hashtags()
    return {"hashtags": hashtags, "total": len(hashtags)}


@router.get("/api/waywo-projects/{project_id}", tags=["projects"])
async def get_waywo_project(project_id: int):
    """
    Get a single WaywoProject with full details.

    Includes the source comment and parent post information.
    """
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    # Get the source comment
    source_comment = get_comment(project.source_comment_id)

    # Get the parent post if available
    parent_post = None
    if source_comment and source_comment.parent:
        parent_post = get_post(source_comment.parent)

    return {
        "project": project.model_dump(),
        "source_comment": source_comment.model_dump() if source_comment else None,
        "parent_post": parent_post.model_dump() if parent_post else None,
    }


@router.delete("/api/waywo-projects/{project_id}", tags=["projects"])
async def delete_waywo_project(project_id: int):
    """
    Delete a single WaywoProject.

    Returns success status and the deleted project ID.
    """
    deleted = delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    return JSONResponse(
        content={
            "status": "deleted",
            "project_id": project_id,
            "message": f"Project {project_id} has been deleted",
        }
    )


@router.post("/api/waywo-projects/{project_id}/bookmark", tags=["projects"])
async def toggle_project_bookmark(project_id: int):
    """
    Toggle bookmark status for a project.

    Returns the new bookmark status.
    """
    new_status = toggle_bookmark(project_id)
    if new_status is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    return JSONResponse(
        content={
            "is_bookmarked": new_status,
            "project_id": project_id,
        }
    )


@router.get("/api/waywo-projects/{project_id}/similar", tags=["projects"])
async def get_similar_waywo_projects(
    project_id: int,
    limit: int = Query(
        default=5, ge=1, le=20, description="Number of similar projects to return"
    ),
):
    """
    Get projects similar to the specified project using vector similarity.

    Uses the project's embedding to find the most similar projects.
    Returns empty list if the project has no embedding.
    """
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    results = get_similar_projects(project_id=project_id, limit=limit)

    return {
        "similar_projects": [
            {
                "project": proj.model_dump(),
                "similarity": round(similarity, 4),
            }
            for proj, similarity in results
        ],
        "project_id": project_id,
    }
