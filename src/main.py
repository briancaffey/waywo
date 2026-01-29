from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.celery_app import debug_task
from src.models import NatQueryRequest, ProcessWaywoPostsRequest, WaywoPostSummary
from src.nat_client import generate as nat_generate
from src.nat_client import health_check as nat_health_check
from src.redis_client import (
    get_all_comments,
    get_all_post_ids,
    get_comment,
    get_comment_count_for_post,
    get_comments_for_post,
    get_post,
    get_total_comment_count,
)
from src.tasks import process_waywo_posts

app = FastAPI(
    title="Waywo Backend",
    version="0.1.0",
    description="An searchable index of 'What are you working on?' projects from Hacker News",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    print("✅ FastAPI application has started")


@app.get("/", tags=["root"])
async def read_root():
    return {"message": "what are you working on?"}


@app.get("/api/health", tags=["health"])
async def healthcheck():
    """
    Application-level health check endpoint.
    Dockerfile uses a separate check script,
    so this is the public HTTP health endpoint.
    """
    return JSONResponse(content={"status": "ok"})


@app.post("/api/debug/celery-task", tags=["debug"])
async def trigger_debug_task():
    """
    Trigger a simple debug Celery task for testing purposes.

    This endpoint calls a Celery task that logs a success message.
    Returns the task ID for tracking the task execution.
    """
    task = debug_task.apply_async()
    return JSONResponse(
        content={
            "status": "task_queued",
            "task_id": task.id,
            "message": "Debug Celery task has been queued",
        }
    )


@app.post("/api/process-waywo-posts", tags=["waywo"])
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


@app.get("/api/waywo-posts", tags=["waywo"])
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


@app.get("/api/waywo-posts/chart-data", tags=["waywo"])
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


@app.get("/api/waywo-posts/{post_id}", tags=["waywo"])
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


@app.get("/api/waywo-comments", tags=["waywo"])
async def list_waywo_comments(limit: int = 50, offset: int = 0):
    """
    List all stored WaywoComment entries with pagination.
    """
    comments = get_all_comments(limit=limit, offset=offset)
    total = get_total_comment_count()

    return {
        "comments": [c.model_dump() for c in comments],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/waywo-comments/{comment_id}", tags=["waywo"])
async def get_waywo_comment(comment_id: int):
    """
    Get a single WaywoComment.
    """
    comment = get_comment(comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail=f"Comment {comment_id} not found")

    # Also fetch the parent post info if available
    parent_post = None
    if comment.parent:
        parent_post = get_post(comment.parent)

    return {
        "comment": comment.model_dump(),
        "parent_post": parent_post.model_dump() if parent_post else None,
    }


@app.get("/api/nat/health", tags=["nat"])
async def nat_service_health():
    """
    Check if the NAT service is healthy.
    """
    is_healthy = await nat_health_check()
    if not is_healthy:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "message": "NAT service is not reachable"},
        )
    return JSONResponse(content={"status": "healthy"})


@app.post("/api/nat/query", tags=["nat"])
async def query_nat_service(request: NatQueryRequest):
    """
    Send a query to the NAT service and get an LLM response.

    This is a simple test endpoint to verify the NAT integration.
    Default message is 'Hello, who are you?'
    """
    try:
        response = await nat_generate(request.message)
        return JSONResponse(content={"status": "success", "response": response})
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to get response from NAT service: {str(e)}",
        )
