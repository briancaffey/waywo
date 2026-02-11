import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.db.database import init_db
from src.settings import MEDIA_DIR
from src.tracing import init_tracing

from src.routes import (
    admin,
    comments,
    generate,
    health,
    posts,
    projects,
    search,
    videos,
    voice,
    workflows,
)

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

# Mount static files for media (screenshots, etc.)
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# Include route modules
app.include_router(health.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(projects.router)
app.include_router(search.router)
app.include_router(admin.router)
app.include_router(videos.router)
app.include_router(voice.router)
app.include_router(workflows.router)
app.include_router(generate.router)


@app.on_event("startup")
async def startup_event():
    init_db()
    init_tracing(service_name="waywo-backend")
    print("FastAPI application has started")
