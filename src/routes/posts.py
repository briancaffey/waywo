import re
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.clients.hn import fetch_item
from src.db.client import (
    get_all_post_ids,
    get_comment_count_for_post,
    get_comments_for_post,
    get_post,
)
from src.models import (
    AddWaywoPostRequest,
    ProcessCommentsRequest,
    ProcessWaywoPostsRequest,
    WaywoPostSummary,
)
from src.worker.tasks import (
    process_waywo_comments,
    process_waywo_post,
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


@router.post("/api/waywo-posts/add", tags=["waywo"])
async def add_waywo_post(request: AddWaywoPostRequest):
    """
    Add a new WaywoPost by HN URL.

    Extracts the post ID from the URL, fetches the post to detect
    year/month from its timestamp, then queues a task to save the
    post and fetch all its comments.
    """
    # Extract HN item ID from URL
    match = re.search(r"(?:id=|item\?id=)(\d+)", request.url)
    if not match:
        # Maybe they just pasted a raw numeric ID
        stripped = request.url.strip()
        if stripped.isdigit():
            post_id = int(stripped)
        else:
            raise HTTPException(
                status_code=400,
                detail="Could not extract HN item ID from URL. Expected a URL like https://news.ycombinator.com/item?id=12345",
            )
    else:
        post_id = int(match.group(1))

    # Check if post already exists
    existing = get_post(post_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Post {post_id} already exists ({existing.title})",
        )

    # Fetch the post from HN API to detect year/month
    post_data = fetch_item(post_id)
    if post_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch item {post_id} from Hacker News API",
        )

    if post_data.get("type") != "story":
        raise HTTPException(
            status_code=400,
            detail=f"Item {post_id} is a '{post_data.get('type')}', not a story",
        )

    # Detect year/month from HN post timestamp
    hn_time = post_data.get("time")
    if hn_time:
        dt = datetime.utcfromtimestamp(hn_time)
        year = dt.year
        month = dt.month
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Item {post_id} has no timestamp",
        )

    # Queue the task to save post + fetch comments
    task = process_waywo_post.delay(
        post_id=post_id,
        year=year,
        month=month,
    )

    return JSONResponse(
        content={
            "status": "task_queued",
            "task_id": task.id,
            "post_id": post_id,
            "title": post_data.get("title"),
            "year": year,
            "month": month,
            "descendants": post_data.get("descendants"),
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

    # Aggregate by (year, month) - sum comment counts for months with multiple posts
    monthly_data: dict[tuple[int, int], dict] = {}
    no_date_posts = []

    for item in posts_data:
        if item["year"] and item["month"]:
            key = (item["year"], item["month"])
            if key in monthly_data:
                monthly_data[key]["comment_count"] += item["comment_count"]
                monthly_data[key]["total_comments"] += item["total_comments"]
            else:
                monthly_data[key] = {
                    "year": item["year"],
                    "month": item["month"],
                    "comment_count": item["comment_count"],
                    "total_comments": item["total_comments"],
                    "label": f"{item['month']:02d}/{str(item['year'])[-2:]}",
                    "tooltip_title": f"{month_names[item['month'] - 1]} {item['year']}",
                }
        else:
            no_date_posts.append(
                {
                    "year": 0,
                    "month": 0,
                    "comment_count": item["comment_count"],
                    "total_comments": item["total_comments"],
                    "label": f"#{item['id']}",
                    "tooltip_title": f"Post #{item['id']}",
                }
            )

    # Sort by year and month
    aggregated = sorted(monthly_data.values(), key=lambda x: (x["year"], x["month"]))
    aggregated.extend(no_date_posts)

    return {
        "posts": aggregated,
        "total_posts": len(post_ids),
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
