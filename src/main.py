from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.celery_app import debug_task

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
    return {"message": "Welcome to the Waywo backend!"}


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
