from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.models import GenerateIdeasRequest, GenerateIdeasResponse
from src.worker.tasks import generate_ideas

router = APIRouter()


@router.post("/api/generate-ideas", tags=["generate"], response_model=GenerateIdeasResponse)
async def create_generate_ideas(request: GenerateIdeasRequest):
    """Enqueue a Celery task to generate synthetic project ideas.

    Returns the task ID for polling status.
    """
    task = generate_ideas.delay(
        num_ideas=request.num_ideas,
        seed_tags=request.seed_tags,
        creativity=request.creativity,
    )

    return GenerateIdeasResponse(
        task_id=task.id,
        num_requested=request.num_ideas,
        seed_tags=request.seed_tags or [],
    )


@router.get("/api/generate-ideas/{task_id}/status", tags=["generate"])
async def get_generate_ideas_status(task_id: str):
    """Poll the status of a generate-ideas Celery task.

    Returns task state and result/progress metadata.
    """
    from src.worker.app import celery_app

    result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "state": result.state,
    }

    if result.state == "STARTED":
        # Task is running — include progress metadata
        meta = result.info or {}
        response["stage"] = meta.get("stage", "unknown")
        response["progress"] = meta.get("progress", 0)
        response["total"] = meta.get("total", 0)
    elif result.state == "SUCCESS":
        # Task completed — include full result
        response["result"] = result.result
    elif result.state == "FAILURE":
        # Task failed — include error info
        response["error"] = str(result.result)

    return JSONResponse(content=response)
