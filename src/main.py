import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.celery_app import debug_task
from src.database import init_db
from src.tracing import init_tracing
from src.embedding_client import (
    EmbeddingError,
    check_embedding_service_health,
    get_single_embedding,
)
from src.db_client import (
    delete_project,
    get_all_comments,
    get_all_hashtags,
    get_all_post_ids,
    get_all_projects,
    get_comment,
    get_comment_count_for_post,
    get_comments_for_post,
    get_database_stats,
    get_post,
    get_project,
    get_projects_for_comment,
    get_projects_with_embeddings_count,
    get_total_comment_count,
    get_total_project_count,
    reset_all_data,
    semantic_search,
)
from src.models import (
    NatQueryRequest,
    ProcessCommentsRequest,
    ProcessWaywoPostsRequest,
    WaywoPostSummary,
)
from src.nat_client import generate as nat_generate
from src.nat_client import health_check as nat_health_check
from src.tasks import process_waywo_comment, process_waywo_comments, process_waywo_posts

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
    init_db()
    init_tracing(service_name="waywo-backend")
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


@app.post("/api/process-waywo-comments", tags=["waywo"])
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


@app.get("/api/waywo-comments/{comment_id}", tags=["waywo"])
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


@app.post("/api/waywo-comments/{comment_id}/process", tags=["waywo"])
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


# =============================================================================
# Projects API
# =============================================================================


@app.get("/api/waywo-projects", tags=["projects"])
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
):
    """
    List all WaywoProject entries with pagination and filtering.

    Filters:
    - comment_id: Filter by source comment
    - tags: Comma-separated list of hashtags to filter by
    - min/max_idea_score: Filter by idea score range
    - min/max_complexity_score: Filter by complexity score range
    - is_valid: Filter by validity status
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
        )
        total = get_total_project_count(is_valid=is_valid)

    return {
        "projects": [p.model_dump() for p in projects],
        "total": total,
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
        },
    }


@app.get("/api/waywo-projects/hashtags", tags=["projects"])
async def list_project_hashtags():
    """
    Get all unique hashtags used across projects.

    Useful for tag autocomplete/filtering.
    """
    hashtags = get_all_hashtags()
    return {"hashtags": hashtags, "total": len(hashtags)}


@app.get("/api/waywo-projects/{project_id}", tags=["projects"])
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


@app.delete("/api/waywo-projects/{project_id}", tags=["projects"])
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


# =============================================================================
# Semantic Search & RAG Chatbot API
# =============================================================================


class SemanticSearchRequest(BaseModel):
    """Request body for semantic search."""

    query: str = Field(..., min_length=1, description="Search query text")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results to return")


class ChatbotRequest(BaseModel):
    """Request body for chatbot query."""

    query: str = Field(..., min_length=1, description="User's question or message")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of projects for context")


@app.get("/api/embedding/health", tags=["semantic"])
async def embedding_service_health():
    """
    Check if the embedding service is healthy.
    """
    embedding_url = os.environ.get("EMBEDDING_URL", "http://192.168.5.96:8000")
    is_healthy = await check_embedding_service_health(embedding_url)

    if not is_healthy:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": "Embedding service is not reachable",
                "url": embedding_url,
            },
        )

    return JSONResponse(
        content={
            "status": "healthy",
            "url": embedding_url,
        }
    )


@app.get("/api/semantic-search/stats", tags=["semantic"])
async def semantic_search_stats():
    """
    Get statistics about semantic search capabilities.
    """
    total_projects = get_total_project_count()
    projects_with_embeddings = get_projects_with_embeddings_count()

    return {
        "total_projects": total_projects,
        "projects_with_embeddings": projects_with_embeddings,
        "embedding_coverage": (
            round(projects_with_embeddings / total_projects * 100, 1)
            if total_projects > 0
            else 0
        ),
    }


@app.post("/api/semantic-search", tags=["semantic"])
async def perform_semantic_search(request: SemanticSearchRequest):
    """
    Perform semantic search over projects using vector similarity.

    Returns the most similar projects based on the query embedding.
    """
    embedding_url = os.environ.get("EMBEDDING_URL", "http://192.168.5.96:8000")

    try:
        # Get embedding for the query
        query_embedding = await get_single_embedding(
            text=request.query,
            embedding_url=embedding_url,
        )
    except EmbeddingError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Embedding service error: {str(e)}",
        )

    # Perform semantic search
    results = semantic_search(
        query_embedding=query_embedding,
        limit=request.limit,
        is_valid=True,
    )

    # Format results
    formatted_results = [
        {
            "project": project.model_dump(),
            "similarity": round(similarity, 4),
        }
        for project, similarity in results
    ]

    return {
        "results": formatted_results,
        "query": request.query,
        "total": len(formatted_results),
    }


@app.post("/api/waywo-chatbot", tags=["semantic"])
async def chatbot_query(request: ChatbotRequest):
    """
    Query the RAG chatbot about projects.

    Uses semantic search to find relevant projects and generates
    a conversational response using an LLM.
    """
    from src.workflows.waywo_chatbot_workflow import run_chatbot_query

    embedding_url = os.environ.get("EMBEDDING_URL", "http://192.168.5.96:8000")

    try:
        result = await run_chatbot_query(
            query=request.query,
            embedding_url=embedding_url,
            top_k=request.top_k,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chatbot error: {str(e)}",
        )

    return {
        "response": result.response,
        "source_projects": result.source_projects,
        "query": result.query,
        "projects_found": result.projects_found,
    }


# =============================================================================
# Admin API
# =============================================================================


@app.get("/api/admin/services-health", tags=["admin"])
async def get_services_health():
    """
    Check health status of external services (LLM, Embedder).
    """
    import httpx

    llm_base_url = os.environ.get("LLM_BASE_URL", "http://192.168.6.19:8002/v1")
    llm_model_name = os.environ.get("LLM_MODEL_NAME", "")
    embedding_url = os.environ.get("EMBEDDING_URL", "http://192.168.5.96:8000")

    services = {}

    # Check LLM server
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{llm_base_url}/models")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("id", "unknown") for m in data.get("data", [])]
                services["llm"] = {
                    "status": "healthy",
                    "url": llm_base_url,
                    "configured_model": llm_model_name,
                    "available_models": models,
                }
            else:
                services["llm"] = {
                    "status": "unhealthy",
                    "url": llm_base_url,
                    "error": f"HTTP {response.status_code}",
                }
    except Exception as e:
        services["llm"] = {
            "status": "unhealthy",
            "url": llm_base_url,
            "error": str(e),
        }

    # Check Embedding server
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{embedding_url}/health")
            if response.status_code == 200:
                services["embedder"] = {
                    "status": "healthy",
                    "url": embedding_url,
                }
            else:
                services["embedder"] = {
                    "status": "unhealthy",
                    "url": embedding_url,
                    "error": f"HTTP {response.status_code}",
                }
    except Exception as e:
        services["embedder"] = {
            "status": "unhealthy",
            "url": embedding_url,
            "error": str(e),
        }

    return services


@app.get("/api/admin/stats", tags=["admin"])
async def get_admin_stats():
    """
    Get database statistics for the admin dashboard.
    """
    import redis

    stats = get_database_stats()

    # Get Redis stats
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.from_url(redis_url)
        redis_info = r.info()
        redis_keys = r.dbsize()
        stats["redis_keys_count"] = redis_keys
        stats["redis_memory_used"] = redis_info.get("used_memory_human", "unknown")
        stats["redis_connected"] = True
    except Exception as e:
        stats["redis_keys_count"] = 0
        stats["redis_memory_used"] = "unknown"
        stats["redis_connected"] = False
        stats["redis_error"] = str(e)

    return stats


@app.delete("/api/admin/reset-sqlite", tags=["admin"])
async def reset_sqlite_database():
    """
    Delete all data from the SQLite database.

    WARNING: This will delete all posts, comments, and projects!
    """
    try:
        result = reset_all_data()
        return JSONResponse(
            content={
                "status": "success",
                "message": "SQLite database has been reset",
                **result,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset SQLite database: {str(e)}",
        )


@app.delete("/api/admin/reset-redis", tags=["admin"])
async def reset_redis_database():
    """
    Flush all data from Redis.

    WARNING: This will delete all Redis keys including Celery task data!
    """
    import redis

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    try:
        r = redis.from_url(redis_url)
        r.flushall()
        return JSONResponse(
            content={
                "status": "success",
                "message": "Redis database has been flushed",
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to flush Redis: {str(e)}",
        )


@app.delete("/api/admin/reset-all", tags=["admin"])
async def reset_all_databases():
    """
    Reset both SQLite and Redis databases.

    WARNING: This will delete ALL data!
    """
    import redis

    errors = []
    results = {}

    # Reset SQLite
    try:
        sqlite_result = reset_all_data()
        results["sqlite"] = {
            "status": "success",
            **sqlite_result,
        }
    except Exception as e:
        errors.append(f"SQLite: {str(e)}")
        results["sqlite"] = {"status": "error", "error": str(e)}

    # Reset Redis
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.from_url(redis_url)
        r.flushall()
        results["redis"] = {"status": "success", "message": "flushed"}
    except Exception as e:
        errors.append(f"Redis: {str(e)}")
        results["redis"] = {"status": "error", "error": str(e)}

    if errors:
        return JSONResponse(
            status_code=207,  # Multi-Status
            content={
                "status": "partial",
                "message": "Some databases failed to reset",
                "errors": errors,
                "results": results,
            },
        )

    return JSONResponse(
        content={
            "status": "success",
            "message": "All databases have been reset",
            "results": results,
        }
    )


@app.get("/api/workflow-prompts", tags=["workflow"])
async def get_workflow_prompts():
    """
    Return every workflow step and its associated prompt template.

    Useful for inspecting and iterating on the prompts used during
    the comment-processing and chatbot pipelines.
    """
    from src.workflows.prompts import WORKFLOW_STEPS

    return {
        "steps": WORKFLOW_STEPS,
        "total": len(WORKFLOW_STEPS),
    }


@app.post("/api/admin/rebuild-vector-index", tags=["admin"])
async def rebuild_vector_index():
    """
    Rebuild the vector quantization index for semantic search.

    Call this after adding new embeddings to enable fast vector search.
    Safe to call multiple times.
    """
    from src.database import build_vector_index

    try:
        build_vector_index()
        return JSONResponse(
            content={
                "status": "success",
                "message": "Vector index rebuilt successfully",
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rebuild vector index: {str(e)}",
        )
