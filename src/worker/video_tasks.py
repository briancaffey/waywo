"""Celery tasks for video generation."""

import asyncio

from src.db.projects import get_project
from src.db.videos import create_video, update_video_status
from src.settings import INVOKEAI_URL, MEDIA_DIR, STT_URL, TTS_URL
from src.worker.app import celery_app


async def run_video_workflow_async(
    project_id: int,
    video_id: int,
    tts_url: str,
    stt_url: str,
    invokeai_url: str,
    media_dir: str,
) -> dict:
    """Run the WaywoVideoWorkflow asynchronously."""
    from src.workflows.waywo_video_workflow import WaywoVideoWorkflow

    workflow = WaywoVideoWorkflow(
        timeout=600,
        tts_url=tts_url,
        stt_url=stt_url,
        invokeai_url=invokeai_url,
        media_dir=media_dir,
    )
    return await workflow.run(
        project_id=project_id,
        video_id=video_id,
    )


@celery_app.task(name="generate_video", bind=True, max_retries=3)
def generate_video_task(self, project_id: int) -> dict:
    """
    Generate a complete video for a project.

    Creates a new video record, runs the full workflow (script -> TTS ->
    STT -> image gen -> assembly), and updates status on success/failure.
    Each Celery retry creates a new video version.

    Args:
        project_id: The project ID to generate a video for.

    Returns:
        Summary dict with video_id, video_path, and duration.
    """
    import nest_asyncio

    nest_asyncio.apply()

    print(f"Starting video generation for project {project_id}")

    # Validate project exists
    project = get_project(project_id)
    if project is None:
        print(f"Project {project_id} not found, skipping")
        return {
            "status": "error",
            "project_id": project_id,
            "message": "Project not found",
        }

    # Create a new video record (each retry gets a new version)
    video_id = create_video(project_id)
    print(f"Created video {video_id} for project {project_id}")

    try:
        result = asyncio.run(
            run_video_workflow_async(
                project_id=project_id,
                video_id=video_id,
                tts_url=TTS_URL,
                stt_url=STT_URL,
                invokeai_url=INVOKEAI_URL,
                media_dir=MEDIA_DIR,
            )
        )
    except Exception as e:
        print(f"Video workflow failed for project {project_id}: {e}")
        update_video_status(video_id, "failed", error_message=str(e))
        raise self.retry(exc=e, countdown=2**self.request.retries)

    print(f"Video generation completed for project {project_id}: {result}")

    return {
        "status": "success",
        "project_id": project_id,
        "video_id": video_id,
        **result,
    }
