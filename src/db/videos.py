"""Video and video segment CRUD operations."""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import func

from src.db.database import SessionLocal
from src.db.models import WaywoVideoDB, WaywoVideoSegmentDB
from src.models import WaywoVideo, WaywoVideoSegment


def get_db_session():
    return SessionLocal()


# ---------------------------------------------------------------------------
# Helper: convert DB row to Pydantic model
# ---------------------------------------------------------------------------


def _segment_from_db(s: WaywoVideoSegmentDB) -> WaywoVideoSegment:
    """Convert a WaywoVideoSegmentDB row to a WaywoVideoSegment Pydantic model."""
    return WaywoVideoSegment(
        id=s.id,
        video_id=s.video_id,
        segment_index=s.segment_index,
        segment_type=s.segment_type,
        narration_text=s.narration_text,
        scene_description=s.scene_description,
        image_prompt=s.image_prompt,
        visual_style=s.visual_style,
        transition=s.transition,
        audio_path=s.audio_path,
        audio_duration_seconds=s.audio_duration_seconds,
        image_path=s.image_path,
        image_name=s.image_name,
        transcription=(
            json.loads(s.transcription_json) if s.transcription_json else None
        ),
        status=s.status,
        error_message=s.error_message,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _video_from_db(v: WaywoVideoDB, include_segments: bool = False) -> WaywoVideo:
    """Convert a WaywoVideoDB row to a WaywoVideo Pydantic model."""
    segments = []
    if include_segments:
        segments = [_segment_from_db(s) for s in v.segments]

    return WaywoVideo(
        id=v.id,
        project_id=v.project_id,
        version=v.version,
        video_title=v.video_title,
        video_style=v.video_style,
        script_json=json.loads(v.script_json) if v.script_json else None,
        voice_name=v.voice_name,
        status=v.status,
        error_message=v.error_message,
        video_path=v.video_path,
        thumbnail_path=v.thumbnail_path,
        duration_seconds=v.duration_seconds,
        width=v.width,
        height=v.height,
        workflow_logs=json.loads(v.workflow_logs) if v.workflow_logs else [],
        view_count=v.view_count,
        is_favorited=v.is_favorited,
        created_at=v.created_at,
        completed_at=v.completed_at,
        segments=segments,
    )


# ---------------------------------------------------------------------------
# Video CRUD
# ---------------------------------------------------------------------------


def create_video(
    project_id: int,
    width: int = 1080,
    height: int = 1920,
) -> int:
    """
    Create a new video record for a project.

    Automatically increments the version number based on existing videos
    for this project. Returns the new video ID.
    """
    db = get_db_session()
    try:
        # Determine next version for this project
        max_version = (
            db.query(func.max(WaywoVideoDB.version))
            .filter(WaywoVideoDB.project_id == project_id)
            .scalar()
        )
        next_version = (max_version or 0) + 1

        db_video = WaywoVideoDB(
            project_id=project_id,
            version=next_version,
            width=width,
            height=height,
            status="pending",
        )
        db.add(db_video)
        db.commit()
        db.refresh(db_video)
        return db_video.id
    finally:
        db.close()


def get_video(video_id: int, include_segments: bool = True) -> WaywoVideo | None:
    """Retrieve a video by ID, optionally with segments."""
    db = get_db_session()
    try:
        db_video = db.query(WaywoVideoDB).filter(WaywoVideoDB.id == video_id).first()
        if db_video is None:
            return None
        return _video_from_db(db_video, include_segments=include_segments)
    finally:
        db.close()


def get_videos_for_project(project_id: int) -> list[WaywoVideo]:
    """Get all video versions for a project, newest first."""
    db = get_db_session()
    try:
        db_videos = (
            db.query(WaywoVideoDB)
            .filter(WaywoVideoDB.project_id == project_id)
            .order_by(WaywoVideoDB.version.desc())
            .all()
        )
        return [_video_from_db(v, include_segments=False) for v in db_videos]
    finally:
        db.close()


def get_all_videos(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
) -> list[WaywoVideo]:
    """Get paginated list of all videos, optionally filtered by status."""
    db = get_db_session()
    try:
        query = db.query(WaywoVideoDB)
        if status is not None:
            query = query.filter(WaywoVideoDB.status == status)
        query = query.order_by(WaywoVideoDB.created_at.desc())
        if offset:
            query = query.offset(offset)
        query = query.limit(limit)
        return [_video_from_db(v, include_segments=False) for v in query.all()]
    finally:
        db.close()


def get_video_feed(
    limit: int = 10,
    offset: int = 0,
    status: str = "completed",
) -> list[WaywoVideo]:
    """Get paginated video feed, filtered by status."""
    db = get_db_session()
    try:
        query = db.query(WaywoVideoDB).filter(WaywoVideoDB.status == status)
        query = query.order_by(WaywoVideoDB.created_at.desc())

        if offset:
            query = query.offset(offset)
        query = query.limit(limit)

        return [_video_from_db(v, include_segments=False) for v in query.all()]
    finally:
        db.close()


def get_video_count(status: str | None = None) -> int:
    """Get total count of videos, optionally filtered by status."""
    db = get_db_session()
    try:
        query = db.query(WaywoVideoDB)
        if status is not None:
            query = query.filter(WaywoVideoDB.status == status)
        return query.count()
    finally:
        db.close()


def update_video_status(
    video_id: int,
    status: str,
    error_message: str | None = None,
) -> bool:
    """Update the generation status of a video. Returns True if updated."""
    db = get_db_session()
    try:
        db_video = db.query(WaywoVideoDB).filter(WaywoVideoDB.id == video_id).first()
        if db_video is None:
            return False
        db_video.status = status
        db_video.error_message = error_message
        if status == "completed":
            db_video.completed_at = datetime.utcnow()
        db.commit()
        return True
    finally:
        db.close()


def update_video_script(
    video_id: int,
    video_title: str,
    video_style: str,
    script_json: dict,
    voice_name: str | None = None,
) -> bool:
    """Update the script data on a video after LLM generation. Returns True if updated."""
    db = get_db_session()
    try:
        db_video = db.query(WaywoVideoDB).filter(WaywoVideoDB.id == video_id).first()
        if db_video is None:
            return False
        db_video.video_title = video_title
        db_video.video_style = video_style
        db_video.script_json = json.dumps(script_json)
        db_video.voice_name = voice_name
        db_video.status = "script_generated"
        db.commit()
        return True
    finally:
        db.close()


def update_video_output(
    video_id: int,
    video_path: str,
    thumbnail_path: str | None = None,
    duration_seconds: float | None = None,
) -> bool:
    """Update the output paths and duration after video assembly. Returns True if updated."""
    db = get_db_session()
    try:
        db_video = db.query(WaywoVideoDB).filter(WaywoVideoDB.id == video_id).first()
        if db_video is None:
            return False
        db_video.video_path = video_path
        db_video.thumbnail_path = thumbnail_path
        db_video.duration_seconds = duration_seconds
        db.commit()
        return True
    finally:
        db.close()


def append_video_workflow_log(video_id: int, log_entry: str) -> bool:
    """Append a log entry to the video's workflow_logs. Returns True if updated."""
    db = get_db_session()
    try:
        db_video = db.query(WaywoVideoDB).filter(WaywoVideoDB.id == video_id).first()
        if db_video is None:
            return False
        logs = json.loads(db_video.workflow_logs) if db_video.workflow_logs else []
        logs.append(log_entry)
        db_video.workflow_logs = json.dumps(logs)
        db.commit()
        return True
    finally:
        db.close()


def toggle_video_favorite(video_id: int) -> bool | None:
    """Toggle favorite status. Returns new status, or None if not found."""
    db = get_db_session()
    try:
        db_video = db.query(WaywoVideoDB).filter(WaywoVideoDB.id == video_id).first()
        if db_video is None:
            return None
        db_video.is_favorited = not db_video.is_favorited
        db.commit()
        return db_video.is_favorited
    finally:
        db.close()


def increment_video_view_count(video_id: int) -> int | None:
    """Increment view count. Returns new count, or None if not found."""
    db = get_db_session()
    try:
        db_video = db.query(WaywoVideoDB).filter(WaywoVideoDB.id == video_id).first()
        if db_video is None:
            return None
        db_video.view_count += 1
        db.commit()
        return db_video.view_count
    finally:
        db.close()


def delete_video(video_id: int) -> bool:
    """Delete a video and all its segments (cascade). Returns True if deleted."""
    db = get_db_session()
    try:
        db_video = db.query(WaywoVideoDB).filter(WaywoVideoDB.id == video_id).first()
        if db_video is None:
            return False
        db.delete(db_video)
        db.commit()
        return True
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Segment CRUD
# ---------------------------------------------------------------------------


def create_segments(video_id: int, segments_data: list[dict]) -> list[int]:
    """
    Bulk-create segments for a video from script data.

    Each dict in segments_data should contain:
        segment_index, segment_type, narration_text, scene_description,
        visual_style, transition

    image_prompt defaults to scene_description if not provided.
    Returns list of created segment IDs.
    """
    db = get_db_session()
    try:
        segment_ids = []
        for seg in segments_data:
            db_seg = WaywoVideoSegmentDB(
                video_id=video_id,
                segment_index=seg["segment_index"],
                segment_type=seg["segment_type"],
                narration_text=seg["narration_text"],
                scene_description=seg["scene_description"],
                image_prompt=seg.get("image_prompt", seg["scene_description"]),
                visual_style=seg.get("visual_style", "abstract"),
                transition=seg.get("transition", "fade"),
                status="pending",
            )
            db.add(db_seg)
            db.flush()
            segment_ids.append(db_seg.id)
        db.commit()
        return segment_ids
    finally:
        db.close()


def get_segment(segment_id: int) -> WaywoVideoSegment | None:
    """Retrieve a single segment by ID."""
    db = get_db_session()
    try:
        db_seg = (
            db.query(WaywoVideoSegmentDB)
            .filter(WaywoVideoSegmentDB.id == segment_id)
            .first()
        )
        if db_seg is None:
            return None
        return _segment_from_db(db_seg)
    finally:
        db.close()


def get_segments_for_video(video_id: int) -> list[WaywoVideoSegment]:
    """Get all segments for a video, ordered by segment_index."""
    db = get_db_session()
    try:
        db_segs = (
            db.query(WaywoVideoSegmentDB)
            .filter(WaywoVideoSegmentDB.video_id == video_id)
            .order_by(WaywoVideoSegmentDB.segment_index)
            .all()
        )
        return [_segment_from_db(s) for s in db_segs]
    finally:
        db.close()


def update_segment_narration(
    segment_id: int,
    narration_text: str,
) -> bool:
    """
    Update the narration text for a segment.

    Clears audio and transcription data so they can be regenerated.
    Returns True if updated.
    """
    db = get_db_session()
    try:
        db_seg = (
            db.query(WaywoVideoSegmentDB)
            .filter(WaywoVideoSegmentDB.id == segment_id)
            .first()
        )
        if db_seg is None:
            return False
        db_seg.narration_text = narration_text
        # Clear audio + transcription so they get regenerated
        db_seg.audio_path = None
        db_seg.audio_duration_seconds = None
        db_seg.transcription_json = None
        db_seg.status = "pending"
        db_seg.error_message = None
        db.commit()
        return True
    finally:
        db.close()


def update_segment_image_prompt(
    segment_id: int,
    image_prompt: str,
) -> bool:
    """
    Update the image prompt for a segment.

    Clears image data so it can be regenerated.
    Returns True if updated.
    """
    db = get_db_session()
    try:
        db_seg = (
            db.query(WaywoVideoSegmentDB)
            .filter(WaywoVideoSegmentDB.id == segment_id)
            .first()
        )
        if db_seg is None:
            return False
        db_seg.image_prompt = image_prompt
        # Clear image so it gets regenerated
        db_seg.image_path = None
        db_seg.image_name = None
        # Revert status if it was complete
        if db_seg.status == "complete":
            db_seg.status = "audio_generated" if db_seg.audio_path else "pending"
        db_seg.error_message = None
        db.commit()
        return True
    finally:
        db.close()


def update_segment_audio(
    segment_id: int,
    audio_path: str,
    audio_duration_seconds: float,
    transcription_json: dict | None = None,
) -> bool:
    """Update audio data for a segment after TTS + STT. Returns True if updated."""
    db = get_db_session()
    try:
        db_seg = (
            db.query(WaywoVideoSegmentDB)
            .filter(WaywoVideoSegmentDB.id == segment_id)
            .first()
        )
        if db_seg is None:
            return False
        db_seg.audio_path = audio_path
        db_seg.audio_duration_seconds = audio_duration_seconds
        if transcription_json is not None:
            db_seg.transcription_json = json.dumps(transcription_json)
        db_seg.status = "audio_generated"
        db_seg.error_message = None
        db.commit()
        return True
    finally:
        db.close()


def update_segment_image(
    segment_id: int,
    image_path: str,
    image_name: str | None = None,
) -> bool:
    """Update image data for a segment after InvokeAI generation. Returns True if updated."""
    db = get_db_session()
    try:
        db_seg = (
            db.query(WaywoVideoSegmentDB)
            .filter(WaywoVideoSegmentDB.id == segment_id)
            .first()
        )
        if db_seg is None:
            return False
        db_seg.image_path = image_path
        db_seg.image_name = image_name
        # Mark complete if audio is also done
        if db_seg.audio_path:
            db_seg.status = "complete"
        else:
            db_seg.status = "image_generated"
        db_seg.error_message = None
        db.commit()
        return True
    finally:
        db.close()


def update_segment_status(
    segment_id: int,
    status: str,
    error_message: str | None = None,
) -> bool:
    """Update the status of a segment. Returns True if updated."""
    db = get_db_session()
    try:
        db_seg = (
            db.query(WaywoVideoSegmentDB)
            .filter(WaywoVideoSegmentDB.id == segment_id)
            .first()
        )
        if db_seg is None:
            return False
        db_seg.status = status
        db_seg.error_message = error_message
        db.commit()
        return True
    finally:
        db.close()


def delete_segment(segment_id: int) -> bool:
    """Delete a single segment. Returns True if deleted."""
    db = get_db_session()
    try:
        count = (
            db.query(WaywoVideoSegmentDB)
            .filter(WaywoVideoSegmentDB.id == segment_id)
            .delete()
        )
        db.commit()
        return count > 0
    finally:
        db.close()
