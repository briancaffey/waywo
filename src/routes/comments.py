from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.db.client import (
    get_all_comments,
    get_comment,
    get_post,
    get_projects_for_comment,
    get_total_comment_count,
)
from src.worker.tasks import process_waywo_comment

router = APIRouter()


@router.get("/api/waywo-comments", tags=["waywo"])
async def list_waywo_comments(
    limit: int = 50,
    offset: int = 0,
    post_id: int | None = None,
):
    """
    List all stored WaywoComment entries with pagination.

    Optionally filter by post_id to get comments for a specific post.
    """
    comments = get_all_comments(limit=limit, offset=offset, post_id=post_id)
    total = get_total_comment_count(post_id=post_id)

    return {
        "comments": [c.model_dump() for c in comments],
        "total": total,
        "limit": limit,
        "offset": offset,
        "post_id": post_id,
    }


@router.get("/api/waywo-comments/{comment_id}", tags=["waywo"])
async def get_waywo_comment(comment_id: int):
    """
    Get a single WaywoComment with its extracted projects.
    """
    comment = get_comment(comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail=f"Comment {comment_id} not found")

    # Also fetch the parent post info if available
    parent_post = None
    if comment.parent:
        parent_post = get_post(comment.parent)

    # Get any extracted projects for this comment
    projects = get_projects_for_comment(comment_id)

    return {
        "comment": comment.model_dump(),
        "parent_post": parent_post.model_dump() if parent_post else None,
        "projects": [p.model_dump() for p in projects],
    }


@router.post("/api/waywo-comments/{comment_id}/process", tags=["waywo"])
async def process_single_comment(comment_id: int):
    """
    Trigger processing of a single comment through the WaywoProjectWorkflow.

    This will extract projects from the specified comment.
    """
    # Verify comment exists
    comment = get_comment(comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail=f"Comment {comment_id} not found")

    task = process_waywo_comment.delay(comment_id=comment_id)
    return JSONResponse(
        content={
            "status": "task_queued",
            "task_id": task.id,
            "comment_id": comment_id,
            "message": f"Processing task queued for comment {comment_id}",
        }
    )
