from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.settings import (
    EMBEDDING_URL,
    INVOKEAI_URL,
    LLM_BASE_URL,
    LLM_MODEL_NAME,
    RERANK_URL,
    REDIS_URL,
    STT_URL,
    TTS_URL,
)
from src.db.client import compute_umap_clusters, get_database_stats, reset_all_data

router = APIRouter()


@router.get("/api/admin/services-health", tags=["admin"])
async def get_services_health():
    """
    Check health status of external services (LLM, Embedder, Reranker).
    """
    import httpx

    services = {}

    # Check LLM server
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LLM_BASE_URL}/models")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("id", "unknown") for m in data.get("data", [])]
                services["llm"] = {
                    "status": "healthy",
                    "url": LLM_BASE_URL,
                    "configured_model": LLM_MODEL_NAME,
                    "available_models": models,
                }
            else:
                services["llm"] = {
                    "status": "unhealthy",
                    "url": LLM_BASE_URL,
                    "error": f"HTTP {response.status_code}",
                }
    except Exception as e:
        services["llm"] = {
            "status": "unhealthy",
            "url": LLM_BASE_URL,
            "error": str(e),
        }

    # Check Embedding server
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{EMBEDDING_URL}/health")
            if response.status_code == 200:
                services["embedder"] = {
                    "status": "healthy",
                    "url": EMBEDDING_URL,
                }
            else:
                services["embedder"] = {
                    "status": "unhealthy",
                    "url": EMBEDDING_URL,
                    "error": f"HTTP {response.status_code}",
                }
    except Exception as e:
        services["embedder"] = {
            "status": "unhealthy",
            "url": EMBEDDING_URL,
            "error": str(e),
        }

    # Check Rerank server
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{RERANK_URL}/health")
            if response.status_code == 200:
                data = response.json()
                services["reranker"] = {
                    "status": "healthy",
                    "url": RERANK_URL,
                    "device": data.get("device", "unknown"),
                }
            else:
                services["reranker"] = {
                    "status": "unhealthy",
                    "url": RERANK_URL,
                    "error": f"HTTP {response.status_code}",
                }
    except Exception as e:
        services["reranker"] = {
            "status": "unhealthy",
            "url": RERANK_URL,
            "error": str(e),
        }

    # Check InvokeAI server
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{INVOKEAI_URL}/api/v1/queue/default/status")
            if response.status_code == 200:
                data = response.json()
                services["invokeai"] = {
                    "status": "healthy",
                    "url": INVOKEAI_URL,
                    "queue_size": data.get("queue_size", 0),
                }
            else:
                services["invokeai"] = {
                    "status": "unhealthy",
                    "url": INVOKEAI_URL,
                    "error": f"HTTP {response.status_code}",
                }
    except Exception as e:
        services["invokeai"] = {
            "status": "unhealthy",
            "url": INVOKEAI_URL,
            "error": str(e),
        }

    # Check TTS server
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{TTS_URL}/v1/audio/list_voices")
            if response.status_code == 200:
                data = response.json()
                # Response is a dict keyed by language group, each with a "voices" list
                voice_count = (
                    sum(
                        len(v.get("voices", []))
                        for v in data.values()
                        if isinstance(v, dict)
                    )
                    if isinstance(data, dict)
                    else len(data) if isinstance(data, list) else 0
                )
                services["tts"] = {
                    "status": "healthy",
                    "url": TTS_URL,
                    "voices": voice_count,
                }
            else:
                services["tts"] = {
                    "status": "unhealthy",
                    "url": TTS_URL,
                    "error": f"HTTP {response.status_code}",
                }
    except Exception as e:
        services["tts"] = {
            "status": "unhealthy",
            "url": TTS_URL,
            "error": str(e),
        }

    # Check STT server
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{STT_URL}/health")
            if response.status_code == 200:
                services["stt"] = {
                    "status": "healthy",
                    "url": STT_URL,
                }
            else:
                services["stt"] = {
                    "status": "unhealthy",
                    "url": STT_URL,
                    "error": f"HTTP {response.status_code}",
                }
    except Exception as e:
        services["stt"] = {
            "status": "unhealthy",
            "url": STT_URL,
            "error": str(e),
        }

    return services


@router.get("/api/admin/stats", tags=["admin"])
async def get_admin_stats():
    """
    Get database statistics for the admin dashboard.
    """
    import redis

    stats = get_database_stats()

    # Get Redis stats
    try:
        r = redis.from_url(REDIS_URL)
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


@router.delete("/api/admin/reset-sqlite", tags=["admin"])
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


@router.delete("/api/admin/reset-redis", tags=["admin"])
async def reset_redis_database():
    """
    Flush all data from Redis.

    WARNING: This will delete all Redis keys including Celery task data!
    """
    import redis

    try:
        r = redis.from_url(REDIS_URL)
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


@router.delete("/api/admin/reset-all", tags=["admin"])
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
    try:
        r = redis.from_url(REDIS_URL)
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


@router.get("/api/workflow-prompts", tags=["workflow"])
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


@router.post("/api/admin/compute-clusters", tags=["admin"])
async def compute_clusters():
    """
    Run UMAP + HDBSCAN on all project embeddings to compute
    2D coordinates and cluster labels for the cluster map visualization.
    """
    try:
        count = compute_umap_clusters()
        return JSONResponse(
            content={
                "status": "success",
                "message": f"Computed clusters for {count} projects",
                "projects_updated": count,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute clusters: {str(e)}",
        )


@router.post("/api/admin/rebuild-vector-index", tags=["admin"])
async def rebuild_vector_index():
    """
    Rebuild the vector quantization index for semantic search.

    Call this after adding new embeddings to enable fast vector search.
    Safe to call multiple times.
    """
    from src.db.database import build_vector_index

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
