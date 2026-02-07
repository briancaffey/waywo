from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.worker.app import debug_task

router = APIRouter()


@router.get("/", tags=["root"])
async def read_root():
    return {"message": "what are you working on?"}


@router.get("/api/health", tags=["health"])
async def healthcheck():
    """
    Application-level health check endpoint.
    Dockerfile uses a separate check script,
    so this is the public HTTP health endpoint.
    """
    return JSONResponse(content={"status": "ok"})


@router.post("/api/debug/celery-task", tags=["debug"])
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
