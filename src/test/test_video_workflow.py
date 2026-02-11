"""Tests for the video generation workflow and Celery task."""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.invokeai import GeneratedImage
from src.clients.stt import TranscriptionResult, WordTimestamp
from src.models import WaywoProject
from src.workflows.video_events import (
    AudioGeneratedEvent,
    AudioTranscribedEvent,
    ImagesGeneratedEvent,
    ProjectLoadedEvent,
    ScriptGeneratedEvent,
)
from src.workflows.waywo_video_workflow import WaywoVideoWorkflow

# Module reference for patch.object calls
import src.workflows.waywo_video_workflow as _wf_mod

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

FAKE_SCRIPT = {
    "video_title": "Test Video",
    "video_style": "energetic",
    "target_duration_seconds": 45,
    "segments": [
        {
            "segment_id": 1,
            "segment_type": "hook",
            "narration_text": "This is a hook.",
            "scene_description": "A bright abstract scene.",
            "visual_style": "abstract",
            "transition": "cut",
        },
        {
            "segment_id": 2,
            "segment_type": "closing",
            "narration_text": "Thanks for watching.",
            "scene_description": "A calm closing scene.",
            "visual_style": "minimal",
            "transition": "fade",
        },
    ],
}


def _fake_project(**overrides):
    defaults = dict(
        id=1,
        source_comment_id=100,
        title="Test Project",
        short_description="A short test project",
        description="This is a test project for testing.",
        hashtags=["test", "demo"],
        project_urls=["https://example.com"],
        url_summaries={"https://example.com": "Example site"},
        idea_score=7,
        complexity_score=5,
        created_at=datetime(2025, 1, 1),
        processed_at=datetime(2025, 1, 1),
    )
    defaults.update(overrides)
    return WaywoProject(**defaults)


def _make_workflow(tmp_path):
    return WaywoVideoWorkflow(
        timeout=60,
        tts_url="http://tts:9000",
        stt_url="http://stt:8001",
        invokeai_url="http://invokeai:9090",
        media_dir=str(tmp_path),
    )


def _fake_wav_bytes(duration: float = 0.5, sample_rate: int = 44100) -> bytes:
    """Build a minimal valid WAV file of the given duration."""
    import struct

    num_samples = int(duration * sample_rate)
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    return header + b"\x00" * data_size


# ---------------------------------------------------------------------------
# Celery task tests
# ---------------------------------------------------------------------------


@pytest.mark.worker
@patch("src.worker.video_tasks.run_video_workflow_async", new_callable=AsyncMock)
@patch("src.worker.video_tasks.create_video", return_value=42)
@patch("src.worker.video_tasks.get_project")
def test_generate_video_task_success(
    mock_get_project, mock_create_video, mock_run_workflow
):
    """Happy path: task creates video, runs workflow, returns result."""
    from src.worker.video_tasks import generate_video_task

    mock_get_project.return_value = _fake_project()
    mock_run_workflow.return_value = {
        "video_id": 42,
        "video_path": "/app/media/videos/42/output.mp4",
        "duration_seconds": 30.5,
    }

    result = generate_video_task(project_id=1)

    assert result["status"] == "success"
    assert result["project_id"] == 1
    assert result["video_id"] == 42
    mock_create_video.assert_called_once_with(1)
    mock_run_workflow.assert_called_once()


@pytest.mark.worker
@patch("src.worker.video_tasks.get_project", return_value=None)
def test_generate_video_task_project_not_found(mock_get_project):
    """Task returns error dict when project does not exist."""
    from src.worker.video_tasks import generate_video_task

    result = generate_video_task(project_id=999)

    assert result["status"] == "error"
    assert "not found" in result["message"].lower()


@pytest.mark.worker
@patch("src.worker.video_tasks.update_video_status")
@patch(
    "src.worker.video_tasks.run_video_workflow_async",
    new_callable=AsyncMock,
    side_effect=RuntimeError("boom"),
)
@patch("src.worker.video_tasks.create_video", return_value=42)
@patch("src.worker.video_tasks.get_project")
def test_generate_video_task_workflow_failure(
    mock_get_project,
    mock_create_video,
    mock_run_workflow,
    mock_update_status,
):
    """Task sets status=failed and raises for retry on workflow error."""
    from src.worker.video_tasks import generate_video_task

    mock_get_project.return_value = _fake_project()

    with pytest.raises(Exception):
        generate_video_task(project_id=1)

    mock_update_status.assert_called_once_with(42, "failed", error_message="boom")


# ---------------------------------------------------------------------------
# Workflow step tests
# ---------------------------------------------------------------------------


@pytest.mark.worker
async def test_workflow_start_step_loads_project(tmp_path):
    """Start step loads project and returns ProjectLoadedEvent."""
    from llama_index.core.workflow import StartEvent

    with (
        patch.object(_wf_mod, "get_project", return_value=_fake_project()),
        patch.object(_wf_mod, "append_video_workflow_log"),
    ):
        workflow = _make_workflow(tmp_path)
        ev = StartEvent(project_id=1, video_id=10)
        result = await workflow.start(ev)

    assert isinstance(result, ProjectLoadedEvent)
    assert result.project_id == 1
    assert result.video_id == 10
    assert result.title == "Test Project"
    assert result.hashtags == ["test", "demo"]


@pytest.mark.worker
async def test_workflow_start_step_project_not_found(tmp_path):
    """Start step raises ValueError when project is not found."""
    from llama_index.core.workflow import StartEvent

    with (
        patch.object(_wf_mod, "get_project", return_value=None),
        patch.object(_wf_mod, "append_video_workflow_log"),
    ):
        workflow = _make_workflow(tmp_path)
        ev = StartEvent(project_id=999, video_id=10)

        with pytest.raises(ValueError, match="not found"):
            await workflow.start(ev)


@pytest.mark.worker
async def test_workflow_generate_script_step(tmp_path):
    """Generate script step calls LLM, picks voice, persists to DB."""
    mock_gen_script = AsyncMock(return_value=FAKE_SCRIPT)
    mock_list_voices = AsyncMock(return_value=[{"name": "English-US.Female-1"}])
    mock_update_script = MagicMock()
    mock_create_segs = MagicMock(return_value=[1, 2])
    mock_update_status = MagicMock()

    with (
        patch.object(_wf_mod, "generate_video_script", mock_gen_script),
        patch.object(_wf_mod, "list_voices", mock_list_voices),
        patch.object(_wf_mod, "update_video_script", mock_update_script),
        patch.object(_wf_mod, "create_segments", mock_create_segs),
        patch.object(_wf_mod, "update_video_status", mock_update_status),
        patch.object(_wf_mod, "append_video_workflow_log"),
    ):
        workflow = _make_workflow(tmp_path)
        ev = ProjectLoadedEvent(
            project_id=1,
            video_id=10,
            title="Test Project",
            short_description="A short test project",
            description="This is a test project.",
            hashtags=["test"],
            url_summaries={},
        )
        result = await workflow.generate_script(ev)

    assert isinstance(result, ScriptGeneratedEvent)
    assert result.script == FAKE_SCRIPT
    assert result.segment_ids == [1, 2]
    assert result.voice_name == "English-US.Female-1"
    mock_update_script.assert_called_once()
    mock_create_segs.assert_called_once()
    mock_update_status.assert_called_once_with(10, "generating")


@pytest.mark.worker
async def test_workflow_generate_audio_step(tmp_path):
    """Generate audio step creates WAV files and reads duration."""
    wav_bytes = _fake_wav_bytes(duration=1.0)
    mock_gen_speech = AsyncMock(return_value=wav_bytes)
    mock_update_audio = MagicMock()

    with (
        patch.object(_wf_mod, "generate_speech", mock_gen_speech),
        patch.object(_wf_mod, "update_segment_audio", mock_update_audio),
        patch.object(_wf_mod, "append_video_workflow_log"),
    ):
        workflow = _make_workflow(tmp_path)
        ev = ScriptGeneratedEvent(
            project_id=1,
            video_id=10,
            title="Test",
            short_description="Short",
            description="Desc",
            hashtags=[],
            url_summaries={},
            script=FAKE_SCRIPT,
            segment_ids=[1, 2],
            voice_name="TestVoice",
        )
        result = await workflow.generate_audio(ev)

    assert isinstance(result, AudioGeneratedEvent)
    assert len(result.audio_paths) == 2
    assert len(result.audio_durations) == 2
    for path in result.audio_paths:
        assert os.path.exists(path)
    for dur in result.audio_durations:
        assert dur > 0
    assert mock_gen_speech.call_count == 2
    assert mock_update_audio.call_count == 2


@pytest.mark.worker
async def test_workflow_transcribe_audio_step(tmp_path):
    """Transcribe step calls STT and converts result to dict."""
    mock_transcribe = AsyncMock(
        return_value=TranscriptionResult(
            text="This is a hook.",
            words=[
                WordTimestamp(word="This", start=0.0, end=0.2),
                WordTimestamp(word="is", start=0.2, end=0.3),
                WordTimestamp(word="a", start=0.3, end=0.4),
                WordTimestamp(word="hook.", start=0.4, end=0.7),
            ],
        )
    )
    mock_update_audio = MagicMock()

    # Create real audio files so file read works
    wav_bytes = _fake_wav_bytes()
    audio_paths = []
    for i in range(2):
        seg_dir = os.path.join(str(tmp_path), "videos", "10", "segments", str(i))
        os.makedirs(seg_dir, exist_ok=True)
        audio_path = os.path.join(seg_dir, "audio.wav")
        with open(audio_path, "wb") as f:
            f.write(wav_bytes)
        audio_paths.append(audio_path)

    with (
        patch.object(_wf_mod, "transcribe_audio", mock_transcribe),
        patch.object(_wf_mod, "update_segment_audio", mock_update_audio),
        patch.object(_wf_mod, "append_video_workflow_log"),
    ):
        workflow = _make_workflow(tmp_path)
        ev = AudioGeneratedEvent(
            project_id=1,
            video_id=10,
            title="Test",
            short_description="Short",
            description="Desc",
            hashtags=[],
            url_summaries={},
            script=FAKE_SCRIPT,
            segment_ids=[1, 2],
            voice_name="TestVoice",
            audio_paths=audio_paths,
            audio_durations=[0.5, 0.5],
        )
        result = await workflow.transcribe_audio_step(ev)

    assert isinstance(result, AudioTranscribedEvent)
    assert len(result.transcriptions) == 2
    assert result.transcriptions[0]["text"] == "This is a hook."
    assert len(result.transcriptions[0]["words"]) == 4
    assert result.transcriptions[0]["words"][0]["word"] == "This"
    assert mock_transcribe.call_count == 2
    assert mock_update_audio.call_count == 2


@pytest.mark.worker
async def test_workflow_generate_images_step(tmp_path):
    """Generate images step calls InvokeAI and saves PNGs."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (768, 1360), color="blue").save(buf, format="PNG")
    fake_png = buf.getvalue()

    mock_gen_image = AsyncMock(
        return_value=GeneratedImage(
            image_name="test_image_abc.png",
            image_bytes=fake_png,
            width=768,
            height=1360,
        )
    )
    mock_update_image = MagicMock()

    with (
        patch.object(_wf_mod, "generate_image", mock_gen_image),
        patch.object(_wf_mod, "update_segment_image", mock_update_image),
        patch.object(_wf_mod, "append_video_workflow_log"),
    ):
        workflow = _make_workflow(tmp_path)
        ev = AudioTranscribedEvent(
            project_id=1,
            video_id=10,
            title="Test",
            short_description="Short",
            description="Desc",
            hashtags=[],
            url_summaries={},
            script=FAKE_SCRIPT,
            segment_ids=[1, 2],
            voice_name="TestVoice",
            audio_paths=["/fake/0/audio.wav", "/fake/1/audio.wav"],
            audio_durations=[0.5, 0.5],
            transcriptions=[
                {"text": "hook", "words": []},
                {"text": "close", "words": []},
            ],
        )
        result = await workflow.generate_images(ev)

    assert isinstance(result, ImagesGeneratedEvent)
    assert len(result.image_paths) == 2
    assert len(result.image_names) == 2
    for path in result.image_paths:
        assert os.path.exists(path)
    assert all(name == "test_image_abc.png" for name in result.image_names)
    assert mock_gen_image.call_count == 2
    assert mock_update_image.call_count == 2


@pytest.mark.worker
async def test_workflow_assemble_video_step(tmp_path):
    """Assemble step calls assemble_video, updates DB, sets completed."""
    from llama_index.core.workflow import StopEvent

    mock_assemble = MagicMock(return_value=30.5)
    mock_add_subs = AsyncMock()
    mock_update_output = MagicMock()
    mock_update_status = MagicMock()

    with (
        patch.object(_wf_mod, "assemble_video", mock_assemble),
        patch.object(_wf_mod, "add_subtitles", mock_add_subs),
        patch.object(_wf_mod, "update_video_output", mock_update_output),
        patch.object(_wf_mod, "update_video_status", mock_update_status),
        patch.object(_wf_mod, "append_video_workflow_log"),
    ):
        workflow = _make_workflow(tmp_path)
        ev = ImagesGeneratedEvent(
            project_id=1,
            video_id=10,
            title="Test",
            short_description="Short",
            description="Desc",
            hashtags=[],
            url_summaries={},
            script=FAKE_SCRIPT,
            segment_ids=[1, 2],
            voice_name="TestVoice",
            audio_paths=["/fake/0/audio.wav", "/fake/1/audio.wav"],
            audio_durations=[2.0, 1.5],
            transcriptions=[
                {"text": "hook", "words": []},
                {"text": "close", "words": []},
            ],
            image_paths=["/fake/0/image.png", "/fake/1/image.png"],
            image_names=["img0.png", "img1.png"],
        )
        result = await workflow.assemble_video_step(ev)

    assert isinstance(result, StopEvent)
    assert result.result["video_id"] == 10
    assert result.result["duration_seconds"] == 30.5

    mock_assemble.assert_called_once()
    call_kwargs = mock_assemble.call_args
    segments_arg = call_kwargs[1].get("segments") or call_kwargs[0][0]
    assert len(segments_arg) == 2

    mock_add_subs.assert_called_once()
    mock_update_output.assert_called_once()
    mock_update_status.assert_called_once_with(10, "completed")
