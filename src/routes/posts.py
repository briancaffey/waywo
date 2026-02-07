from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.db.client import (
    get_all_post_ids,
    get_comment_count_for_post,
    get_comments_for_post,
    get_post,
)
from src.models import (
    ProcessCommentsRequest,
    ProcessWaywoPostsRequest,
    WaywoPostSummary,
)
from src.worker.tasks import (
    process_waywo_comments,
    process_waywo_posts,
)

router = APIRouter()


@router.post("/api/process-waywo-posts", tags=["waywo"])
async def trigger_process_waywo_posts(request: ProcessWaywoPostsRequest = None):
    """
    Trigger processing of WaywoPost entries from waywo.yml.

    Optionally pass limit_posts and limit_comments for testing.
    """
    if request is None:
        request = ProcessWaywoPostsRequest()

    task = process_waywo_posts.delay(
        limit_posts=request.limit_posts,
        limit_comments=request.limit_comments,
    )
    return JSONResponse(
        content={
            "status": "task_queued",
            "task_id": task.id,
            "limit_posts": request.limit_posts,
            "limit_comments": request.limit_comments,
        }
    )


@router.post("/api/process-waywo-comments", tags=["waywo"])
async def trigger_process_waywo_comments(request: ProcessCommentsRequest = None):
    """
    Trigger processing of comments through the WaywoProjectWorkflow.

    This will extract projects from unprocessed comments.
    Optionally pass a limit for testing purposes.
    """
    if request is None:
        request = ProcessCommentsRequest()

    task = process_waywo_comments.delay(
        limit=request.limit,
    )
    return JSONResponse(
        content={
            "status": "task_queued",
            "task_id": task.id,
            "limit": request.limit,
            "message": "Comment processing task has been queued",
        }
    )


@router.get("/api/waywo-posts", tags=["waywo"])
async def list_waywo_posts() -> list[WaywoPostSummary]:
    """
    List all stored WaywoPost entries with comment counts.
    """
    post_ids = get_all_post_ids()
    summaries = []

    for post_id in post_ids:
        post = get_post(post_id)
        if post is None:
            continue

        summary = WaywoPostSummary(
            id=post.id,
            title=post.title,
            year=post.year,
            month=post.month,
            score=post.score,
            comment_count=get_comment_count_for_post(post.id),
            descendants=post.descendants,
        )
        summaries.append(summary)

    # Sort by year and month descending
    summaries.sort(key=lambda x: (x.year or 0, x.month or 0), reverse=True)
    return summaries


@router.get("/api/waywo-posts/chart-data", tags=["waywo"])
async def get_posts_chart_data():
    """
    Get chart data for posts, grouped by month/year.
    Returns comment counts per post, suitable for bar chart visualization.
    """
    post_ids = get_all_post_ids()
    posts_data = []

    for post_id in post_ids:
        post = get_post(post_id)
        if post is None:
            continue

        comment_count = get_comment_count_for_post(post.id)
        posts_data.append(
            {
                "id": post.id,
                "year": post.year,
                "month": post.month,
                "title": post.title,
                "comment_count": comment_count,
                "total_comments": post.descendants or 0,
            }
        )

    # Sort by year and month
    posts_data.sort(key=lambda x: (x["year"] or 0, x["month"] or 0))

    # Create labels like "03/22" (MM/YY format) and tooltip titles
    month_names = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    for item in posts_data:
        if item["year"] and item["month"]:
            item["label"] = f"{item['month']:02d}/{str(item['year'])[-2:]}"
            item["tooltip_title"] = f"{month_names[item['month'] - 1]} {item['year']}"
        else:
            item["label"] = f"#{item['id']}"
            item["tooltip_title"] = f"Post #{item['id']}"

    return {
        "posts": posts_data,
        "total_posts": len(posts_data),
    }


@router.get("/api/waywo-posts/{post_id}", tags=["waywo"])
async def get_waywo_post(post_id: int):
    """
    Get a single WaywoPost with its comments.
    """
    post = get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail=f"Post {post_id} not found")

    comments = get_comments_for_post(post_id)

    return {
        "post": post.model_dump(),
        "comments": [c.model_dump() for c in comments],
        "comment_count": len(comments),
    }
