"""Tests for the subtitle overlay client (pycaps integration)."""

import os
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.stt import TranscriptionResult, WordTimestamp
from src.clients.subtitles import (
    SubtitleError,
    transcription_to_whisper_json,
)

# Module reference for patching
import src.clients.subtitles as _sub_mod


# ---------------------------------------------------------------------------
# transcription_to_whisper_json tests
# ---------------------------------------------------------------------------


@pytest.mark.client
def test_whisper_json_empty_words():
    """Returns empty segments when transcription has no words."""
    result = TranscriptionResult(text="", words=None)
    wj = transcription_to_whisper_json(result)
    assert wj == {"segments": []}


@pytest.mark.client
def test_whisper_json_empty_word_list():
    """Returns empty segments when word list is empty."""
    result = TranscriptionResult(text="", words=[])
    wj = transcription_to_whisper_json(result)
    assert wj == {"segments": []}


@pytest.mark.client
def test_whisper_json_single_word():
    """Single word produces one segment with one word."""
    result = TranscriptionResult(
        text="Hello",
        words=[WordTimestamp(word="Hello", start=0.0, end=0.5)],
    )
    wj = transcription_to_whisper_json(result)

    assert len(wj["segments"]) == 1
    seg = wj["segments"][0]
    assert seg["start"] == 0.0
    assert seg["end"] == 0.5
    assert len(seg["words"]) == 1
    assert seg["words"][0]["word"] == "Hello"


@pytest.mark.client
def test_whisper_json_continuous_speech():
    """Words without pauses form a single segment."""
    result = TranscriptionResult(
        text="Hello world today",
        words=[
            WordTimestamp(word="Hello", start=0.0, end=0.3),
            WordTimestamp(word="world", start=0.35, end=0.7),
            WordTimestamp(word="today", start=0.75, end=1.1),
        ],
    )
    wj = transcription_to_whisper_json(result)

    assert len(wj["segments"]) == 1
    assert len(wj["segments"][0]["words"]) == 3
    assert wj["segments"][0]["start"] == 0.0
    assert wj["segments"][0]["end"] == 1.1


@pytest.mark.client
def test_whisper_json_splits_on_pause():
    """A pause longer than threshold creates a segment boundary."""
    result = TranscriptionResult(
        text="Hello world. Next segment.",
        words=[
            WordTimestamp(word="Hello", start=0.0, end=0.3),
            WordTimestamp(word="world.", start=0.35, end=0.7),
            # 0.5s pause — exceeds default 0.25s threshold
            WordTimestamp(word="Next", start=1.2, end=1.5),
            WordTimestamp(word="segment.", start=1.55, end=1.9),
        ],
    )
    wj = transcription_to_whisper_json(result)

    assert len(wj["segments"]) == 2

    seg0 = wj["segments"][0]
    assert seg0["start"] == 0.0
    assert seg0["end"] == 0.7
    assert [w["word"] for w in seg0["words"]] == ["Hello", "world."]

    seg1 = wj["segments"][1]
    assert seg1["start"] == 1.2
    assert seg1["end"] == 1.9
    assert [w["word"] for w in seg1["words"]] == ["Next", "segment."]


@pytest.mark.client
def test_whisper_json_custom_pause_threshold():
    """Custom pause threshold controls segment splitting."""
    result = TranscriptionResult(
        text="A B C",
        words=[
            WordTimestamp(word="A", start=0.0, end=0.2),
            # 0.3s gap
            WordTimestamp(word="B", start=0.5, end=0.7),
            # 0.3s gap
            WordTimestamp(word="C", start=1.0, end=1.2),
        ],
    )

    # With high threshold, everything stays in one segment
    wj_high = transcription_to_whisper_json(result, pause_threshold=0.5)
    assert len(wj_high["segments"]) == 1

    # With low threshold, each gap creates a split
    wj_low = transcription_to_whisper_json(result, pause_threshold=0.2)
    assert len(wj_low["segments"]) == 3


@pytest.mark.client
def test_whisper_json_multiple_pauses():
    """Multiple pauses create multiple segments (like multi-segment video)."""
    result = TranscriptionResult(
        text="Seg one. Seg two. Seg three.",
        words=[
            WordTimestamp(word="Seg", start=0.0, end=0.2),
            WordTimestamp(word="one.", start=0.25, end=0.5),
            # 0.4s pause
            WordTimestamp(word="Seg", start=0.9, end=1.1),
            WordTimestamp(word="two.", start=1.15, end=1.4),
            # 0.4s pause
            WordTimestamp(word="Seg", start=1.8, end=2.0),
            WordTimestamp(word="three.", start=2.05, end=2.3),
        ],
    )
    wj = transcription_to_whisper_json(result)

    assert len(wj["segments"]) == 3
    assert len(wj["segments"][0]["words"]) == 2
    assert len(wj["segments"][1]["words"]) == 2
    assert len(wj["segments"][2]["words"]) == 2


@pytest.mark.client
def test_whisper_json_word_format():
    """Each word dict has exactly the required whisper_json fields."""
    result = TranscriptionResult(
        text="Test",
        words=[WordTimestamp(word="Test", start=1.5, end=2.0)],
    )
    wj = transcription_to_whisper_json(result)
    word = wj["segments"][0]["words"][0]

    assert set(word.keys()) == {"word", "start", "end"}
    assert word["word"] == "Test"
    assert word["start"] == 1.5
    assert word["end"] == 2.0


# ---------------------------------------------------------------------------
# add_subtitles tests
# ---------------------------------------------------------------------------


@pytest.mark.client
async def test_add_subtitles_happy_path(tmp_path):
    """add_subtitles extracts audio, transcribes, and runs pycaps."""
    from src.clients.subtitles import add_subtitles

    video_in = tmp_path / "input.mp4"
    video_out = tmp_path / "output.mp4"
    video_in.write_bytes(b"fake video content")

    mock_transcribe = AsyncMock(
        return_value=TranscriptionResult(
            text="Hello world",
            words=[
                WordTimestamp(word="Hello", start=0.0, end=0.5),
                WordTimestamp(word="world", start=0.6, end=1.0),
            ],
        )
    )
    mock_extract = MagicMock()
    mock_pycaps = MagicMock()

    with (
        patch.object(_sub_mod, "extract_audio_to_wav", mock_extract),
        patch.object(_sub_mod, "transcribe_audio", mock_transcribe),
        patch.object(_sub_mod, "_run_pycaps_pipeline", mock_pycaps),
    ):
        result = await add_subtitles(video_in, video_out, stt_url="http://stt:8001")

    assert result == video_out
    mock_extract.assert_called_once()
    mock_transcribe.assert_called_once()
    assert mock_transcribe.call_args[1]["timestamps"] is True
    assert mock_transcribe.call_args[1]["stt_url"] == "http://stt:8001"

    mock_pycaps.assert_called_once()
    call_args = mock_pycaps.call_args[0]
    assert call_args[0] == str(video_in)
    assert call_args[1] == str(video_out)
    whisper_json = call_args[2]
    assert len(whisper_json["segments"]) >= 1


@pytest.mark.client
async def test_add_subtitles_no_words_copies_video(tmp_path):
    """When STT returns no words, video is copied without subtitles."""
    from src.clients.subtitles import add_subtitles

    video_in = tmp_path / "input.mp4"
    video_out = tmp_path / "output.mp4"
    video_in.write_bytes(b"fake video content")

    mock_transcribe = AsyncMock(
        return_value=TranscriptionResult(text="", words=[])
    )
    mock_extract = MagicMock()

    with (
        patch.object(_sub_mod, "extract_audio_to_wav", mock_extract),
        patch.object(_sub_mod, "transcribe_audio", mock_transcribe),
    ):
        result = await add_subtitles(video_in, video_out)

    assert result == video_out
    assert video_out.exists()
    assert video_out.read_bytes() == b"fake video content"


@pytest.mark.client
async def test_add_subtitles_propagates_error(tmp_path):
    """add_subtitles wraps errors in SubtitleError."""
    from src.clients.subtitles import add_subtitles

    video_in = tmp_path / "input.mp4"
    video_out = tmp_path / "output.mp4"
    video_in.write_bytes(b"fake")

    mock_extract = MagicMock(side_effect=RuntimeError("ffmpeg not found"))

    with patch.object(_sub_mod, "extract_audio_to_wav", mock_extract):
        with pytest.raises(SubtitleError, match="ffmpeg not found"):
            await add_subtitles(video_in, video_out)


@pytest.mark.client
async def test_add_subtitles_default_stt_url(tmp_path):
    """When stt_url is not provided, transcribe_audio uses its default."""
    from src.clients.subtitles import add_subtitles

    video_in = tmp_path / "input.mp4"
    video_out = tmp_path / "output.mp4"
    video_in.write_bytes(b"fake")

    mock_transcribe = AsyncMock(
        return_value=TranscriptionResult(text="Hi", words=[
            WordTimestamp(word="Hi", start=0.0, end=0.3),
        ])
    )
    mock_extract = MagicMock()
    mock_pycaps = MagicMock()

    with (
        patch.object(_sub_mod, "extract_audio_to_wav", mock_extract),
        patch.object(_sub_mod, "transcribe_audio", mock_transcribe),
        patch.object(_sub_mod, "_run_pycaps_pipeline", mock_pycaps),
    ):
        await add_subtitles(video_in, video_out)

    # stt_url should NOT be in kwargs when not provided
    assert "stt_url" not in mock_transcribe.call_args[1]


# ---------------------------------------------------------------------------
# Workflow integration test
# ---------------------------------------------------------------------------


@pytest.mark.worker
async def test_workflow_assemble_with_subtitles(tmp_path):
    """Assemble step calls add_subtitles after video assembly."""
    from llama_index.core.workflow import StopEvent

    import src.workflows.waywo_video_workflow as _wf_mod
    from src.workflows.waywo_video_workflow import WaywoVideoWorkflow
    from src.workflows.video_events import ImagesGeneratedEvent

    FAKE_SCRIPT = {
        "video_title": "Test",
        "video_style": "energetic",
        "target_duration_seconds": 30,
        "segments": [
            {
                "segment_id": 1,
                "segment_type": "hook",
                "narration_text": "Hello world.",
                "scene_description": "A scene.",
                "transition": "cut",
            }
        ],
    }

    mock_assemble = MagicMock(return_value=15.0)
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
        workflow = WaywoVideoWorkflow(
            timeout=60,
            tts_url="http://tts:9000",
            stt_url="http://stt:8001",
            invokeai_url="http://invokeai:9090",
            media_dir=str(tmp_path),
        )
        ev = ImagesGeneratedEvent(
            project_id=1,
            video_id=10,
            title="Test",
            short_description="Short",
            description="Desc",
            hashtags=[],
            url_summaries={},
            script=FAKE_SCRIPT,
            segment_ids=[1],
            voice_name="TestVoice",
            audio_paths=["/fake/0/audio.wav"],
            audio_durations=[3.0],
            transcriptions=[{"text": "Hello world.", "words": []}],
            image_paths=["/fake/0/image.png"],
            image_names=["img0.png"],
        )
        result = await workflow.assemble_video_step(ev)

    assert isinstance(result, StopEvent)
    assert result.result["duration_seconds"] == 15.0

    # assemble_video writes to the raw path
    raw_path = mock_assemble.call_args[1]["output_path"]
    assert "output_raw.mp4" in raw_path

    # add_subtitles is called with raw -> final
    mock_add_subs.assert_called_once()
    sub_kwargs = mock_add_subs.call_args[1]
    assert "output_raw.mp4" in str(sub_kwargs["video_path"])
    assert "output.mp4" in str(sub_kwargs["output_path"])
    assert sub_kwargs["stt_url"] == "http://stt:8001"


@pytest.mark.worker
async def test_workflow_assemble_subtitle_failure_falls_back(tmp_path):
    """When subtitle generation fails, workflow falls back to raw video."""
    from llama_index.core.workflow import StopEvent

    import src.workflows.waywo_video_workflow as _wf_mod
    from src.workflows.waywo_video_workflow import WaywoVideoWorkflow
    from src.workflows.video_events import ImagesGeneratedEvent

    FAKE_SCRIPT = {
        "video_title": "Test",
        "video_style": "energetic",
        "target_duration_seconds": 30,
        "segments": [
            {
                "segment_id": 1,
                "segment_type": "hook",
                "narration_text": "Hello.",
                "scene_description": "A scene.",
                "transition": "cut",
            }
        ],
    }

    # Create the raw video file so os.rename can work
    video_dir = os.path.join(str(tmp_path), "videos", "10")
    os.makedirs(video_dir, exist_ok=True)
    raw_path = os.path.join(video_dir, "output_raw.mp4")
    with open(raw_path, "wb") as f:
        f.write(b"fake video")

    mock_assemble = MagicMock(return_value=10.0)
    mock_add_subs = AsyncMock(side_effect=RuntimeError("pycaps exploded"))
    mock_update_output = MagicMock()
    mock_update_status = MagicMock()

    with (
        patch.object(_wf_mod, "assemble_video", mock_assemble),
        patch.object(_wf_mod, "add_subtitles", mock_add_subs),
        patch.object(_wf_mod, "update_video_output", mock_update_output),
        patch.object(_wf_mod, "update_video_status", mock_update_status),
        patch.object(_wf_mod, "append_video_workflow_log"),
    ):
        workflow = WaywoVideoWorkflow(
            timeout=60,
            tts_url="http://tts:9000",
            stt_url="http://stt:8001",
            invokeai_url="http://invokeai:9090",
            media_dir=str(tmp_path),
        )
        ev = ImagesGeneratedEvent(
            project_id=1,
            video_id=10,
            title="Test",
            short_description="Short",
            description="Desc",
            hashtags=[],
            url_summaries={},
            script=FAKE_SCRIPT,
            segment_ids=[1],
            voice_name="TestVoice",
            audio_paths=["/fake/0/audio.wav"],
            audio_durations=[3.0],
            transcriptions=[{"text": "Hello.", "words": []}],
            image_paths=["/fake/0/image.png"],
            image_names=["img0.png"],
        )
        result = await workflow.assemble_video_step(ev)

    # Should still complete successfully despite subtitle failure
    assert isinstance(result, StopEvent)
    assert result.result["duration_seconds"] == 10.0
    mock_update_status.assert_called_once_with(10, "completed")

    # The raw file should have been renamed to output.mp4
    final_path = os.path.join(video_dir, "output.mp4")
    assert os.path.exists(final_path)
