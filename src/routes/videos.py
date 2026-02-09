from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.db.client import (
    delete_video,
    get_all_videos,
    get_project,
    get_segment,
    get_video,
    get_video_count,
    get_video_feed,
    get_videos_for_project,
    increment_video_view_count,
    toggle_video_favorite,
    update_segment_image_prompt,
    update_segment_narration,
)
from src.worker.video_tasks import generate_video_task


class UpdateNarrationRequest(BaseModel):
    narration_text: str


class UpdateImagePromptRequest(BaseModel):
    image_prompt: str

router = APIRouter()


@router.get("/api/waywo-videos", tags=["videos"])
async def list_videos(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = Query(None, description="Filter by video status"),
):
    """List all videos with pagination and optional status filter."""
    videos = get_all_videos(limit=limit, offset=offset, status=status)
    total = get_video_count(status=status)

    return {
        "videos": [v.model_dump() for v in videos],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/waywo-videos/feed", tags=["videos"])
async def video_feed(
    limit: int = 10,
    offset: int = 0,
):
    """Public video feed — completed videos only, newest first."""
    videos = get_video_feed(limit=limit, offset=offset)
    total = get_video_count(status="completed")

    return {
        "videos": [v.model_dump() for v in videos],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/waywo-videos/{video_id}", tags=["videos"])
async def get_video_detail(video_id: int):
    """Get a single video with segments and project context."""
    video = get_video(video_id, include_segments=True)
    if video is None:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    project = get_project(video.project_id)

    return {
        "video": video.model_dump(),
        "project": project.model_dump() if project else None,
    }


@router.delete("/api/waywo-videos/{video_id}", tags=["videos"])
async def delete_waywo_video(video_id: int):
    """Delete a video and all its segments."""
    deleted = delete_video(video_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    return JSONResponse(
        content={
            "status": "deleted",
            "video_id": video_id,
            "message": f"Video {video_id} has been deleted",
        }
    )


@router.post("/api/waywo-videos/{video_id}/favorite", tags=["videos"])
async def toggle_favorite(video_id: int):
    """Toggle favorite status for a video."""
    new_status = toggle_video_favorite(video_id)
    if new_status is None:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    return JSONResponse(
        content={
            "is_favorited": new_status,
            "video_id": video_id,
        }
    )


@router.post("/api/waywo-videos/{video_id}/view", tags=["videos"])
async def record_view(video_id: int):
    """Increment view count for a video."""
    new_count = increment_video_view_count(video_id)
    if new_count is None:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    return JSONResponse(
        content={
            "view_count": new_count,
            "video_id": video_id,
        }
    )


@router.post("/api/waywo-projects/{project_id}/generate-video", tags=["videos"])
async def generate_video(project_id: int):
    """Trigger video generation for a project via Celery."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    result = generate_video_task.delay(project_id)

    return JSONResponse(
        content={
            "task_id": result.id,
            "project_id": project_id,
            "message": f"Video generation started for project {project_id}",
        }
    )


@router.get("/api/waywo-projects/{project_id}/videos", tags=["videos"])
async def list_project_videos(project_id: int):
    """List all video versions for a project."""
    videos = get_videos_for_project(project_id)

    return {
        "videos": [v.model_dump() for v in videos],
        "total": len(videos),
        "project_id": project_id,
    }


@router.patch("/api/waywo-videos/segments/{segment_id}/narration", tags=["videos"])
async def update_narration(segment_id: int, body: UpdateNarrationRequest):
    """Update the narration text for a segment (clears audio/transcription)."""
    segment = get_segment(segment_id)
    if segment is None:
        raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")

    update_segment_narration(segment_id, body.narration_text)
    updated = get_segment(segment_id)

    return JSONResponse(
        content={
            "segment": updated.model_dump(mode="json"),
            "message": f"Narration updated for segment {segment_id}",
        }
    )


@router.patch("/api/waywo-videos/segments/{segment_id}/image-prompt", tags=["videos"])
async def update_image_prompt_route(segment_id: int, body: UpdateImagePromptRequest):
    """Update the image prompt for a segment (clears image data)."""
    segment = get_segment(segment_id)
    if segment is None:
        raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")

    update_segment_image_prompt(segment_id, body.image_prompt)
    updated = get_segment(segment_id)

    return JSONResponse(
        content={
            "segment": updated.model_dump(mode="json"),
            "message": f"Image prompt updated for segment {segment_id}",
        }
    )
