"""Tests for database operations using in-memory SQLite."""

import json
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.db.database import Base
from src.db.models import (
    WaywoCommentDB,
    WaywoPostDB,
    WaywoProjectDB,
    WaywoVideoDB,
    WaywoVideoSegmentDB,
)
from src.models import WaywoComment, WaywoPost, WaywoProject

# ---------------------------------------------------------------------------
# In-memory SQLite test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine (no vector extension)."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a test session factory bound to the in-memory engine."""
    TestSession = sessionmaker(bind=test_engine)
    return TestSession


@pytest.fixture(autouse=True)
def patch_db_sessions(test_session):
    """Patch all DB module get_db_session calls to use the test session."""
    with (
        patch("src.db.posts.get_db_session", test_session),
        patch("src.db.comments.get_db_session", test_session),
        patch("src.db.projects.get_db_session", test_session),
        patch("src.db.stats.get_db_session", test_session),
        patch("src.db.search.get_db_session", test_session),
        patch("src.db.videos.get_db_session", test_session),
    ):
        yield


# ---------------------------------------------------------------------------
# Post tests
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_save_and_get_post(sample_post):
    """save_post stores and get_post retrieves a post."""
    from src.db.posts import save_post, get_post

    save_post(sample_post)
    result = get_post(12345)

    assert result is not None
    assert result.id == 12345
    assert result.title == "What are you working on? (December 2025)"
    assert result.year == 2025
    assert result.month == 12
    assert result.kids == [111, 222, 333]


@pytest.mark.db
def test_save_post_update(sample_post):
    """save_post updates existing post."""
    from src.db.posts import save_post, get_post

    save_post(sample_post)

    # Update the post
    sample_post.score = 200
    save_post(sample_post)

    result = get_post(12345)
    assert result.score == 200


@pytest.mark.db
def test_get_post_not_found():
    """get_post returns None for non-existent post."""
    from src.db.posts import get_post

    result = get_post(99999)
    assert result is None


@pytest.mark.db
def test_get_all_post_ids(sample_post):
    """get_all_post_ids returns list of post IDs."""
    from src.db.posts import save_post, get_all_post_ids

    save_post(sample_post)
    ids = get_all_post_ids()

    assert 12345 in ids


# ---------------------------------------------------------------------------
# Comment tests
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_save_and_get_comment(sample_post, sample_comment):
    """save_comment stores and get_comment retrieves a comment."""
    from src.db.posts import save_post
    from src.db.comments import save_comment, get_comment

    # Must save parent post first (FK constraint)
    save_post(sample_post)
    save_comment(sample_comment)

    result = get_comment(111)
    assert result is not None
    assert result.id == 111
    assert result.by == "commenter1"
    assert result.parent == 12345


@pytest.mark.db
def test_comment_exists(sample_post, sample_comment):
    """comment_exists returns True for existing comments."""
    from src.db.posts import save_post
    from src.db.comments import save_comment, comment_exists

    save_post(sample_post)
    save_comment(sample_comment)

    assert comment_exists(111) is True
    assert comment_exists(99999) is False


@pytest.mark.db
def test_get_unprocessed_comments(sample_post, sample_comment):
    """get_unprocessed_comments returns unprocessed comments."""
    from src.db.posts import save_post
    from src.db.comments import save_comment, get_unprocessed_comments

    save_post(sample_post)
    save_comment(sample_comment)

    unprocessed = get_unprocessed_comments(limit=10)
    assert len(unprocessed) == 1
    assert unprocessed[0].id == 111


@pytest.mark.db
def test_mark_comment_processed(sample_post, sample_comment):
    """mark_comment_processed updates processed flag and timestamp."""
    from src.db.posts import save_post
    from src.db.comments import (
        save_comment,
        mark_comment_processed,
        is_comment_processed,
        get_unprocessed_comments,
    )

    save_post(sample_post)
    save_comment(sample_comment)

    assert is_comment_processed(111) is False

    mark_comment_processed(111)

    assert is_comment_processed(111) is True
    assert len(get_unprocessed_comments()) == 0


@pytest.mark.db
def test_get_all_comments(sample_post, sample_comment):
    """get_all_comments returns paginated comments."""
    from src.db.posts import save_post
    from src.db.comments import save_comment, get_all_comments, get_total_comment_count

    save_post(sample_post)
    save_comment(sample_comment)

    comments = get_all_comments(limit=10, offset=0)
    assert len(comments) == 1

    count = get_total_comment_count()
    assert count == 1


@pytest.mark.db
def test_get_comments_for_post(sample_post, sample_comment):
    """get_comments_for_post returns comments linked to a post."""
    from src.db.posts import save_post
    from src.db.comments import save_comment, get_comments_for_post

    save_post(sample_post)
    save_comment(sample_comment)

    comments = get_comments_for_post(12345)
    assert len(comments) == 1
    assert comments[0].id == 111


# ---------------------------------------------------------------------------
# Project tests
# ---------------------------------------------------------------------------


def _make_project(source_comment_id=111, **overrides):
    """Helper to create a WaywoProject."""
    now = datetime.utcnow()
    defaults = dict(
        id=0,
        source_comment_id=source_comment_id,
        is_valid_project=True,
        title="Test Project",
        short_description="Short desc",
        description="Long description here.",
        hashtags=["python", "web"],
        project_urls=["https://example.com"],
        url_summaries={},
        primary_url="https://example.com",
        url_contents={},
        idea_score=7,
        complexity_score=4,
        created_at=now,
        processed_at=now,
        workflow_logs=[],
    )
    defaults.update(overrides)
    return WaywoProject(**defaults)


@pytest.mark.db
def test_save_and_get_project(sample_post, sample_comment):
    """save_project stores and get_project retrieves a project."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project, get_project

    save_post(sample_post)
    save_comment(sample_comment)

    project = _make_project()
    project_id = save_project(project)

    assert project_id is not None
    assert project_id > 0

    result = get_project(project_id)
    assert result is not None
    assert result.title == "Test Project"
    assert result.hashtags == ["python", "web"]
    assert result.idea_score == 7


@pytest.mark.db
def test_save_project_with_embedding(sample_post, sample_comment):
    """save_project stores embedding blob."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project

    save_post(sample_post)
    save_comment(sample_comment)

    project = _make_project()
    embedding = [0.1, 0.2, 0.3, 0.4]
    project_id = save_project(project, embedding=embedding)

    assert project_id > 0


@pytest.mark.db
def test_delete_project(sample_post, sample_comment):
    """delete_project removes a project by ID."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project, delete_project, get_project

    save_post(sample_post)
    save_comment(sample_comment)

    project = _make_project()
    project_id = save_project(project)

    assert delete_project(project_id) is True
    assert get_project(project_id) is None
    assert delete_project(99999) is False


@pytest.mark.db
def test_toggle_bookmark(sample_post, sample_comment):
    """toggle_bookmark flips bookmark status."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project, toggle_bookmark

    save_post(sample_post)
    save_comment(sample_comment)

    project = _make_project()
    project_id = save_project(project)

    # Initially not bookmarked
    result = toggle_bookmark(project_id)
    assert result is True

    # Toggle back
    result = toggle_bookmark(project_id)
    assert result is False

    # Non-existent project
    assert toggle_bookmark(99999) is None


@pytest.mark.db
def test_get_all_projects(sample_post, sample_comment):
    """get_all_projects returns filtered project list."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project, get_all_projects, get_total_project_count

    save_post(sample_post)
    save_comment(sample_comment)

    save_project(_make_project(idea_score=8, complexity_score=3))
    save_project(_make_project(idea_score=4, complexity_score=7))

    # No filters
    all_projects = get_all_projects()
    assert len(all_projects) == 2

    # Filter by idea score
    filtered = get_all_projects(min_idea_score=6)
    assert len(filtered) == 1

    # Count
    assert get_total_project_count() == 2


@pytest.mark.db
def test_get_all_hashtags(sample_post, sample_comment):
    """get_all_hashtags returns deduplicated sorted tags."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project, get_all_hashtags

    save_post(sample_post)
    save_comment(sample_comment)

    save_project(_make_project(hashtags=["python", "web"]))
    save_project(_make_project(hashtags=["python", "ai"]))

    tags = get_all_hashtags()
    assert "python" in tags
    assert "web" in tags
    assert "ai" in tags
    # Should be deduplicated
    assert tags.count("python") == 1


@pytest.mark.db
def test_get_bookmarked_count(sample_post, sample_comment):
    """get_bookmarked_count returns number of bookmarked projects."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project, toggle_bookmark, get_bookmarked_count

    save_post(sample_post)
    save_comment(sample_comment)

    pid1 = save_project(_make_project())
    save_project(_make_project())

    assert get_bookmarked_count() == 0

    toggle_bookmark(pid1)
    assert get_bookmarked_count() == 1


# ---------------------------------------------------------------------------
# Stats tests
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_get_database_stats(sample_post, sample_comment):
    """get_database_stats returns correct counts."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project
    from src.db.stats import get_database_stats

    save_post(sample_post)
    save_comment(sample_comment)
    save_project(_make_project())

    stats = get_database_stats()
    assert stats["posts_count"] == 1
    assert stats["comments_count"] == 1
    assert stats["projects_count"] == 1


@pytest.mark.db
def test_reset_all_data(sample_post, sample_comment):
    """reset_all_data deletes all records."""
    from src.db.posts import save_post, get_all_post_ids
    from src.db.comments import save_comment
    from src.db.projects import save_project
    from src.db.stats import reset_all_data

    save_post(sample_post)
    save_comment(sample_comment)
    save_project(_make_project())

    result = reset_all_data()
    assert result["posts_deleted"] == 1
    assert result["comments_deleted"] == 1
    assert result["projects_deleted"] == 1

    assert get_all_post_ids() == []


# ---------------------------------------------------------------------------
# Video tests
# ---------------------------------------------------------------------------


def _setup_project(sample_post, sample_comment):
    """Helper: create a post + comment + project, return project_id."""
    from src.db.posts import save_post
    from src.db.comments import save_comment
    from src.db.projects import save_project

    save_post(sample_post)
    save_comment(sample_comment)
    return save_project(_make_project())


@pytest.mark.db
def test_create_video(sample_post, sample_comment):
    """create_video creates a video with auto-incrementing version."""
    from src.db.videos import create_video, get_video

    project_id = _setup_project(sample_post, sample_comment)

    video_id = create_video(project_id)
    assert video_id > 0

    video = get_video(video_id)
    assert video is not None
    assert video.project_id == project_id
    assert video.version == 1
    assert video.status == "pending"
    assert video.width == 1080
    assert video.height == 1920


@pytest.mark.db
def test_create_video_auto_version(sample_post, sample_comment):
    """create_video auto-increments version for the same project."""
    from src.db.videos import create_video, get_video

    project_id = _setup_project(sample_post, sample_comment)

    vid1 = create_video(project_id)
    vid2 = create_video(project_id)

    v1 = get_video(vid1)
    v2 = get_video(vid2)
    assert v1.version == 1
    assert v2.version == 2


@pytest.mark.db
def test_get_videos_for_project(sample_post, sample_comment):
    """get_videos_for_project returns all versions, newest first."""
    from src.db.videos import create_video, get_videos_for_project

    project_id = _setup_project(sample_post, sample_comment)

    create_video(project_id)
    create_video(project_id)

    videos = get_videos_for_project(project_id)
    assert len(videos) == 2
    assert videos[0].version == 2
    assert videos[1].version == 1


@pytest.mark.db
def test_update_video_status(sample_post, sample_comment):
    """update_video_status changes status and sets completed_at."""
    from src.db.videos import create_video, get_video, update_video_status

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    assert update_video_status(video_id, "generating") is True
    assert get_video(video_id).status == "generating"

    assert update_video_status(video_id, "completed") is True
    video = get_video(video_id)
    assert video.status == "completed"
    assert video.completed_at is not None

    # Non-existent video
    assert update_video_status(99999, "failed") is False


@pytest.mark.db
def test_update_video_status_failed(sample_post, sample_comment):
    """update_video_status stores error message on failure."""
    from src.db.videos import create_video, get_video, update_video_status

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    update_video_status(video_id, "failed", error_message="TTS service unavailable")
    video = get_video(video_id)
    assert video.status == "failed"
    assert video.error_message == "TTS service unavailable"


@pytest.mark.db
def test_update_video_script(sample_post, sample_comment):
    """update_video_script stores script metadata."""
    from src.db.videos import create_video, get_video, update_video_script

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    script = {"segments": [{"narration_text": "Hello"}]}
    update_video_script(
        video_id,
        video_title="Test Video",
        video_style="energetic",
        script_json=script,
        voice_name="Magpie-Multilingual.EN-US.Mia.Happy",
    )

    video = get_video(video_id)
    assert video.video_title == "Test Video"
    assert video.video_style == "energetic"
    assert video.script_json == script
    assert video.voice_name == "Magpie-Multilingual.EN-US.Mia.Happy"
    assert video.status == "script_generated"


@pytest.mark.db
def test_update_video_output(sample_post, sample_comment):
    """update_video_output stores output paths and duration."""
    from src.db.videos import create_video, get_video, update_video_output

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    update_video_output(
        video_id,
        video_path="/media/videos/1/video.mp4",
        thumbnail_path="/media/videos/1/thumb.jpg",
        duration_seconds=42.5,
    )

    video = get_video(video_id)
    assert video.video_path == "/media/videos/1/video.mp4"
    assert video.thumbnail_path == "/media/videos/1/thumb.jpg"
    assert video.duration_seconds == 42.5


@pytest.mark.db
def test_append_video_workflow_log(sample_post, sample_comment):
    """append_video_workflow_log accumulates log entries."""
    from src.db.videos import create_video, get_video, append_video_workflow_log

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    append_video_workflow_log(video_id, "Script generated")
    append_video_workflow_log(video_id, "Audio generated")

    video = get_video(video_id)
    assert video.workflow_logs == ["Script generated", "Audio generated"]


@pytest.mark.db
def test_toggle_video_favorite(sample_post, sample_comment):
    """toggle_video_favorite flips favorite status."""
    from src.db.videos import create_video, toggle_video_favorite

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    assert toggle_video_favorite(video_id) is True
    assert toggle_video_favorite(video_id) is False
    assert toggle_video_favorite(99999) is None


@pytest.mark.db
def test_increment_video_view_count(sample_post, sample_comment):
    """increment_video_view_count increments and returns new count."""
    from src.db.videos import create_video, increment_video_view_count

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    assert increment_video_view_count(video_id) == 1
    assert increment_video_view_count(video_id) == 2
    assert increment_video_view_count(99999) is None


@pytest.mark.db
def test_delete_video_cascades_segments(sample_post, sample_comment):
    """delete_video removes video and all its segments."""
    from src.db.videos import (
        create_video,
        create_segments,
        delete_video,
        get_video,
        get_segments_for_video,
    )

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    create_segments(
        video_id,
        [
            {
                "segment_index": 0,
                "segment_type": "hook",
                "narration_text": "Hello!",
                "scene_description": "A cool scene",
            },
        ],
    )

    assert delete_video(video_id) is True
    assert get_video(video_id) is None
    assert get_segments_for_video(video_id) == []
    assert delete_video(99999) is False


@pytest.mark.db
def test_get_video_feed(sample_post, sample_comment):
    """get_video_feed returns completed videos, newest first."""
    from src.db.videos import (
        create_video,
        update_video_status,
        get_video_feed,
        get_video_count,
    )

    project_id = _setup_project(sample_post, sample_comment)

    vid1 = create_video(project_id)
    vid2 = create_video(project_id)
    create_video(project_id)  # stays pending

    update_video_status(vid1, "completed")
    update_video_status(vid2, "completed")

    feed = get_video_feed(limit=10)
    assert len(feed) == 2

    assert get_video_count() == 3
    assert get_video_count(status="completed") == 2
    assert get_video_count(status="pending") == 1


# ---------------------------------------------------------------------------
# Video Segment tests
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_create_and_get_segments(sample_post, sample_comment):
    """create_segments bulk-creates and get_segments_for_video retrieves them."""
    from src.db.videos import create_video, create_segments, get_segments_for_video

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    segment_ids = create_segments(
        video_id,
        [
            {
                "segment_index": 0,
                "segment_type": "hook",
                "narration_text": "Ever wondered...",
                "scene_description": "Abstract neon visualization",
                "visual_style": "abstract",
                "transition": "fade",
            },
            {
                "segment_index": 1,
                "segment_type": "features",
                "narration_text": "It features...",
                "scene_description": "Screenshot of the app",
                "visual_style": "screenshot",
                "transition": "cut",
            },
        ],
    )

    assert len(segment_ids) == 2

    segments = get_segments_for_video(video_id)
    assert len(segments) == 2
    assert segments[0].segment_index == 0
    assert segments[0].segment_type == "hook"
    assert segments[0].narration_text == "Ever wondered..."
    assert (
        segments[0].image_prompt == "Abstract neon visualization"
    )  # defaults to scene_description
    assert segments[0].status == "pending"
    assert segments[1].segment_index == 1
    assert segments[1].transition == "cut"


@pytest.mark.db
def test_create_segments_custom_image_prompt(sample_post, sample_comment):
    """create_segments respects explicit image_prompt."""
    from src.db.videos import create_video, create_segments, get_segment

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    seg_ids = create_segments(
        video_id,
        [
            {
                "segment_index": 0,
                "segment_type": "hook",
                "narration_text": "Hello",
                "scene_description": "Original LLM description",
                "image_prompt": "Custom edited prompt",
            },
        ],
    )

    seg = get_segment(seg_ids[0])
    assert seg.scene_description == "Original LLM description"
    assert seg.image_prompt == "Custom edited prompt"


@pytest.mark.db
def test_update_segment_narration(sample_post, sample_comment):
    """update_segment_narration clears audio and resets status."""
    from src.db.videos import (
        create_video,
        create_segments,
        get_segment,
        update_segment_audio,
        update_segment_narration,
    )

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    seg_ids = create_segments(
        video_id,
        [
            {
                "segment_index": 0,
                "segment_type": "hook",
                "narration_text": "Original text",
                "scene_description": "A scene",
            },
        ],
    )

    # Simulate audio generation
    update_segment_audio(seg_ids[0], "/audio/seg0.wav", 5.2, {"text": "Original text"})
    seg = get_segment(seg_ids[0])
    assert seg.status == "audio_generated"
    assert seg.audio_path is not None

    # Edit narration - should clear audio
    update_segment_narration(seg_ids[0], "New edited text")
    seg = get_segment(seg_ids[0])
    assert seg.narration_text == "New edited text"
    assert seg.audio_path is None
    assert seg.audio_duration_seconds is None
    assert seg.transcription is None
    assert seg.status == "pending"


@pytest.mark.db
def test_update_segment_image_prompt(sample_post, sample_comment):
    """update_segment_image_prompt clears image and adjusts status."""
    from src.db.videos import (
        create_video,
        create_segments,
        get_segment,
        update_segment_audio,
        update_segment_image,
        update_segment_image_prompt,
    )

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    seg_ids = create_segments(
        video_id,
        [
            {
                "segment_index": 0,
                "segment_type": "hook",
                "narration_text": "Hello",
                "scene_description": "Original scene",
            },
        ],
    )

    # Simulate complete segment
    update_segment_audio(seg_ids[0], "/audio/seg0.wav", 5.2)
    update_segment_image(seg_ids[0], "/images/seg0.png", "invoke-abc.png")
    seg = get_segment(seg_ids[0])
    assert seg.status == "complete"

    # Edit image prompt - should clear image but keep audio
    update_segment_image_prompt(seg_ids[0], "New image prompt")
    seg = get_segment(seg_ids[0])
    assert seg.image_prompt == "New image prompt"
    assert seg.scene_description == "Original scene"  # preserved
    assert seg.image_path is None
    assert seg.image_name is None
    assert seg.status == "audio_generated"  # reverted since audio still exists


@pytest.mark.db
def test_update_segment_audio(sample_post, sample_comment):
    """update_segment_audio stores audio data and transcription."""
    from src.db.videos import (
        create_video,
        create_segments,
        get_segment,
        update_segment_audio,
    )

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    seg_ids = create_segments(
        video_id,
        [
            {
                "segment_index": 0,
                "segment_type": "hook",
                "narration_text": "Hello world",
                "scene_description": "A scene",
            },
        ],
    )

    transcription = {
        "text": "hello world",
        "words": [
            {"word": "hello", "start": 0.0, "end": 0.32},
            {"word": "world", "start": 0.35, "end": 0.72},
        ],
    }
    update_segment_audio(seg_ids[0], "/audio/seg0.wav", 0.72, transcription)

    seg = get_segment(seg_ids[0])
    assert seg.audio_path == "/audio/seg0.wav"
    assert seg.audio_duration_seconds == 0.72
    assert seg.transcription == transcription
    assert seg.status == "audio_generated"


@pytest.mark.db
def test_update_segment_image(sample_post, sample_comment):
    """update_segment_image stores image data and completes segment if audio exists."""
    from src.db.videos import (
        create_video,
        create_segments,
        get_segment,
        update_segment_audio,
        update_segment_image,
    )

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    seg_ids = create_segments(
        video_id,
        [
            {
                "segment_index": 0,
                "segment_type": "hook",
                "narration_text": "Hello",
                "scene_description": "A scene",
            },
        ],
    )

    # Image without audio -> image_generated
    update_segment_image(seg_ids[0], "/images/seg0.png", "invoke-123.png")
    seg = get_segment(seg_ids[0])
    assert seg.status == "image_generated"

    # Now add audio -> complete
    update_segment_audio(seg_ids[0], "/audio/seg0.wav", 3.0)
    update_segment_image(seg_ids[0], "/images/seg0.png", "invoke-123.png")
    seg = get_segment(seg_ids[0])
    assert seg.status == "complete"


@pytest.mark.db
def test_delete_segment(sample_post, sample_comment):
    """delete_segment removes a single segment."""
    from src.db.videos import (
        create_video,
        create_segments,
        delete_segment,
        get_segment,
        get_segments_for_video,
    )

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    seg_ids = create_segments(
        video_id,
        [
            {
                "segment_index": 0,
                "segment_type": "hook",
                "narration_text": "Hello",
                "scene_description": "A scene",
            },
            {
                "segment_index": 1,
                "segment_type": "closing",
                "narration_text": "Goodbye",
                "scene_description": "Another scene",
            },
        ],
    )

    assert delete_segment(seg_ids[0]) is True
    assert get_segment(seg_ids[0]) is None
    assert len(get_segments_for_video(video_id)) == 1
    assert delete_segment(99999) is False


@pytest.mark.db
def test_get_video_with_segments(sample_post, sample_comment):
    """get_video with include_segments=True returns segments in order."""
    from src.db.videos import create_video, create_segments, get_video

    project_id = _setup_project(sample_post, sample_comment)
    video_id = create_video(project_id)

    create_segments(
        video_id,
        [
            {
                "segment_index": 1,
                "segment_type": "closing",
                "narration_text": "Goodbye",
                "scene_description": "End scene",
            },
            {
                "segment_index": 0,
                "segment_type": "hook",
                "narration_text": "Hello",
                "scene_description": "Start scene",
            },
        ],
    )

    video = get_video(video_id, include_segments=True)
    assert len(video.segments) == 2
    # Ordered by segment_index
    assert video.segments[0].segment_index == 0
    assert video.segments[0].narration_text == "Hello"
    assert video.segments[1].segment_index == 1
    assert video.segments[1].narration_text == "Goodbye"

    # Without segments
    video_no_seg = get_video(video_id, include_segments=False)
    assert video_no_seg.segments == []
