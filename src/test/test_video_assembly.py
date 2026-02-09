"""Tests for video assembly (MoviePy-based)."""

import os
import struct
import tempfile

import numpy as np
import pytest
from PIL import Image

from src.clients.video import (
    VideoAssemblyError,
    _load_and_scale_image,
    _make_ken_burns_frame_func,
    _pick_motion,
    assemble_video,
)

# ---------------------------------------------------------------------------
# Fixtures — synthetic images and audio
# ---------------------------------------------------------------------------


def _make_test_png(path: str, width: int = 768, height: int = 1360, color=(255, 0, 0)):
    """Create a solid-color PNG for testing."""
    img = Image.new("RGB", (width, height), color)
    img.save(path, "PNG")


def _make_silent_wav(path: str, duration: float = 2.0, sample_rate: int = 44100):
    """Create a silent WAV file with a known duration."""
    num_samples = int(duration * sample_rate)
    data_size = num_samples * 2  # 16-bit mono
    with open(path, "wb") as f:
        # RIFF header
        f.write(struct.pack("<4sI4s", b"RIFF", 36 + data_size, b"WAVE"))
        # fmt chunk
        f.write(
            struct.pack(
                "<4sIHHIIHH", b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16
            )
        )
        # data chunk
        f.write(struct.pack("<4sI", b"data", data_size))
        f.write(b"\x00" * data_size)


# ---------------------------------------------------------------------------
# _load_and_scale_image tests
# ---------------------------------------------------------------------------


@pytest.mark.client
def test_load_and_scale_image():
    """_load_and_scale_image resizes to overscan dimensions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        png_path = os.path.join(tmpdir, "test.png")
        _make_test_png(png_path, 768, 1360)

        result = _load_and_scale_image(png_path, 1080, 1920, overscan=1.1)

        # Expected overscan: 1188 x 2112
        assert result.shape == (2112, 1188, 3)
        assert result.dtype == np.uint8


@pytest.mark.client
def test_load_and_scale_image_no_overscan():
    """_load_and_scale_image with overscan=1.0 produces exact target size."""
    with tempfile.TemporaryDirectory() as tmpdir:
        png_path = os.path.join(tmpdir, "test.png")
        _make_test_png(png_path, 768, 1360)

        result = _load_and_scale_image(png_path, 1080, 1920, overscan=1.0)

        assert result.shape == (1920, 1080, 3)


# ---------------------------------------------------------------------------
# Ken Burns frame function tests
# ---------------------------------------------------------------------------


@pytest.mark.client
def test_ken_burns_frame_func_returns_correct_shape():
    """Ken Burns frame function returns frames of the correct shape."""
    width, height = 1080, 1920
    overscan = 1.1
    os_w, os_h = int(width * overscan), int(height * overscan)
    image = np.random.randint(0, 255, (os_h, os_w, 3), dtype=np.uint8)

    for motion in ["zoom_in", "zoom_out", "pan_left", "pan_right"]:
        frame_func = _make_ken_burns_frame_func(image, width, height, 3.0, motion)

        # Check at t=0
        frame_start = frame_func(0.0)
        assert frame_start.shape == (height, width, 3), f"{motion} t=0 shape mismatch"

        # Check at t=duration
        frame_end = frame_func(3.0)
        assert frame_end.shape == (height, width, 3), f"{motion} t=end shape mismatch"

        # Check at midpoint
        frame_mid = frame_func(1.5)
        assert frame_mid.shape == (height, width, 3), f"{motion} t=mid shape mismatch"


@pytest.mark.client
def test_ken_burns_different_motions_produce_different_frames():
    """Different Ken Burns motions produce different frame content."""
    width, height = 108, 192  # Small for speed
    overscan = 1.1
    os_w, os_h = int(width * overscan), int(height * overscan)
    # Use a gradient image so different crops yield different content
    image = np.zeros((os_h, os_w, 3), dtype=np.uint8)
    for y in range(os_h):
        for x in range(os_w):
            image[y, x] = [x % 256, y % 256, (x + y) % 256]

    frames_at_end = {}
    for motion in ["zoom_in", "zoom_out", "pan_left", "pan_right"]:
        frame_func = _make_ken_burns_frame_func(image, width, height, 3.0, motion)
        frames_at_end[motion] = frame_func(3.0)

    # At least some motions should produce different frames at t=end
    pairs_differ = 0
    motions = list(frames_at_end.keys())
    for i in range(len(motions)):
        for j in range(i + 1, len(motions)):
            if not np.array_equal(frames_at_end[motions[i]], frames_at_end[motions[j]]):
                pairs_differ += 1

    assert pairs_differ > 0, "All motions produced identical frames"


@pytest.mark.client
def test_ken_burns_zoom_in_changes_over_time():
    """Zoom-in motion produces different frames at start vs end."""
    width, height = 108, 192
    overscan = 1.1
    os_w, os_h = int(width * overscan), int(height * overscan)
    image = np.random.randint(0, 255, (os_h, os_w, 3), dtype=np.uint8)

    frame_func = _make_ken_burns_frame_func(image, width, height, 3.0, "zoom_in")
    frame_start = frame_func(0.0)
    frame_end = frame_func(3.0)

    assert not np.array_equal(frame_start, frame_end), "Zoom-in frames should differ"


# ---------------------------------------------------------------------------
# _pick_motion tests
# ---------------------------------------------------------------------------


@pytest.mark.client
def test_pick_motion_cycles():
    """_pick_motion cycles through 4 presets deterministically."""
    motions = [_pick_motion(i) for i in range(8)]
    assert motions[:4] == ["zoom_in", "zoom_out", "pan_left", "pan_right"]
    assert motions[4:8] == ["zoom_in", "zoom_out", "pan_left", "pan_right"]


# ---------------------------------------------------------------------------
# assemble_video tests
# ---------------------------------------------------------------------------


@pytest.mark.client
def test_assemble_video_empty_segments():
    """assemble_video raises for empty segment list."""
    with pytest.raises(VideoAssemblyError, match="No segments provided"):
        assemble_video([], "/tmp/out.mp4")


@pytest.mark.client
def test_assemble_video_single_segment():
    """assemble_video produces an MP4 from a single segment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        png_path = os.path.join(tmpdir, "img.png")
        wav_path = os.path.join(tmpdir, "audio.wav")
        out_path = os.path.join(tmpdir, "output.mp4")

        _make_test_png(png_path, 768, 1360, color=(0, 128, 255))
        _make_silent_wav(wav_path, duration=2.0)

        segments = [
            {
                "image_path": png_path,
                "audio_path": wav_path,
                "audio_duration_seconds": 2.0,
                "transition": "cut",
            }
        ]

        duration = assemble_video(segments, out_path, width=270, height=480, fps=10)

        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 0
        assert abs(duration - 2.0) < 0.1


@pytest.mark.client
def test_assemble_video_multiple_segments():
    """assemble_video handles 3 segments with different transitions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        transitions = ["cut", "fade", "slide_left"]
        segments = []

        for i, (color, trans) in enumerate(zip(colors, transitions)):
            png_path = os.path.join(tmpdir, f"img_{i}.png")
            wav_path = os.path.join(tmpdir, f"audio_{i}.wav")
            _make_test_png(png_path, 768, 1360, color=color)
            _make_silent_wav(wav_path, duration=1.5)
            segments.append(
                {
                    "image_path": png_path,
                    "audio_path": wav_path,
                    "audio_duration_seconds": 1.5,
                    "transition": trans,
                }
            )

        out_path = os.path.join(tmpdir, "output.mp4")
        duration = assemble_video(segments, out_path, width=270, height=480, fps=10)

        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 0
        # 3 segments * 1.5s - 2 transitions * 0.5s overlap = 3.5s
        assert duration > 0


@pytest.mark.client
def test_assemble_video_cut_transition_no_overlap():
    """Cut transitions produce total duration equal to sum of segments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        segments = []
        for i in range(2):
            png_path = os.path.join(tmpdir, f"img_{i}.png")
            wav_path = os.path.join(tmpdir, f"audio_{i}.wav")
            _make_test_png(png_path, 768, 1360)
            _make_silent_wav(wav_path, duration=2.0)
            segments.append(
                {
                    "image_path": png_path,
                    "audio_path": wav_path,
                    "audio_duration_seconds": 2.0,
                    "transition": "cut",
                }
            )

        out_path = os.path.join(tmpdir, "output.mp4")
        duration = assemble_video(segments, out_path, width=270, height=480, fps=10)

        # Two 2s segments + 0.3s gap = 4.3s total
        assert abs(duration - 4.3) < 0.1


@pytest.mark.client
def test_assemble_video_fade_transition_no_overlap():
    """Fade transitions now use hard cuts with gap (no overlap)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        segments = []
        for i in range(2):
            png_path = os.path.join(tmpdir, f"img_{i}.png")
            wav_path = os.path.join(tmpdir, f"audio_{i}.wav")
            _make_test_png(png_path, 768, 1360)
            _make_silent_wav(wav_path, duration=2.0)
            segments.append(
                {
                    "image_path": png_path,
                    "audio_path": wav_path,
                    "audio_duration_seconds": 2.0,
                    "transition": "fade",
                }
            )

        out_path = os.path.join(tmpdir, "output.mp4")
        duration = assemble_video(
            segments,
            out_path,
            width=270,
            height=480,
            fps=10,
            transition_duration=0.5,
        )

        # Two 2s segments + 0.3s gap = 4.3s (no overlap regardless of transition)
        assert abs(duration - 4.3) < 0.1
