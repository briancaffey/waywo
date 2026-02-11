"""Video assembly using MoviePy 2.x.

Stitches AI-generated images and TTS audio into an MP4 video with
Ken Burns effects and transitions between segments.
"""

import logging
import struct
from typing import Callable

import numpy as np
from moviepy import AudioFileClip, CompositeVideoClip, VideoClip, afx
from PIL import Image

logger = logging.getLogger(__name__)

# Ken Burns motion presets
MOTIONS = ["zoom_in", "zoom_out", "pan_left", "pan_right"]


class VideoAssemblyError(Exception):
    """Exception raised when video assembly fails."""

    pass


def _load_and_scale_image(
    image_path: str, width: int, height: int, overscan: float = 1.1
) -> np.ndarray:
    """Load an image and resize to overscan dimensions for Ken Burns.

    Args:
        image_path: Path to the source image.
        width: Target output width (before overscan).
        height: Target output height (before overscan).
        overscan: Scale factor for Ken Burns headroom (default 1.1 = 110%).

    Returns:
        Numpy RGB array at (overscan_height, overscan_width, 3).
    """
    img = Image.open(image_path).convert("RGB")
    os_w = int(width * overscan)
    os_h = int(height * overscan)
    img = img.resize((os_w, os_h), Image.LANCZOS)
    return np.array(img)


def _pick_motion(segment_index: int) -> str:
    """Pick a deterministic Ken Burns motion preset based on segment index."""
    return MOTIONS[segment_index % len(MOTIONS)]


def _make_ken_burns_frame_func(
    image: np.ndarray,
    width: int,
    height: int,
    duration: float,
    motion: str,
) -> Callable[[float], np.ndarray]:
    """Create a frame function that applies a Ken Burns effect.

    The image should be oversized (110% of target). The frame function
    crops a target-sized window that moves/zooms over the duration.

    Args:
        image: Oversized numpy RGB array.
        width: Output frame width.
        height: Output frame height.
        duration: Clip duration in seconds.
        motion: One of "zoom_in", "zoom_out", "pan_left", "pan_right".

    Returns:
        A callable (t) -> numpy RGB array of shape (height, width, 3).
    """
    img_h, img_w = image.shape[:2]
    # Maximum offset available for panning
    max_dx = img_w - width
    max_dy = img_h - height

    def frame_func(t: float) -> np.ndarray:
        progress = t / duration if duration > 0 else 0.0
        progress = max(0.0, min(1.0, progress))

        if motion == "zoom_in":
            # Start showing full oversized image, end cropped to target
            scale = 1.0 - progress * (1.0 - width / img_w)
            cur_w = int(img_w * scale)
            cur_h = int(img_h * scale)
            x = (img_w - cur_w) // 2
            y = (img_h - cur_h) // 2
            crop = image[y : y + cur_h, x : x + cur_w]
            return np.array(
                Image.fromarray(crop).resize((width, height), Image.LANCZOS)
            )

        elif motion == "zoom_out":
            # Start cropped to target, end showing full oversized image
            scale = width / img_w + progress * (1.0 - width / img_w)
            cur_w = int(img_w * scale)
            cur_h = int(img_h * scale)
            x = (img_w - cur_w) // 2
            y = (img_h - cur_h) // 2
            crop = image[y : y + cur_h, x : x + cur_w]
            return np.array(
                Image.fromarray(crop).resize((width, height), Image.LANCZOS)
            )

        elif motion == "pan_left":
            # Crop window slides from right to left
            x = int(max_dx * (1.0 - progress))
            y = max_dy // 2
            return image[y : y + height, x : x + width].copy()

        elif motion == "pan_right":
            # Crop window slides from left to right
            x = int(max_dx * progress)
            y = max_dy // 2
            return image[y : y + height, x : x + width].copy()

        else:
            # Fallback: center crop
            x = max_dx // 2
            y = max_dy // 2
            return image[y : y + height, x : x + width].copy()

    return frame_func


def _make_silent_audio_bytes(duration: float, sample_rate: int = 44100) -> bytes:
    """Generate a minimal silent WAV file as bytes.

    Used as fallback when a segment has no audio file.
    """
    num_samples = int(duration * sample_rate)
    # WAV header (44 bytes) + data
    data_size = num_samples * 2  # 16-bit mono
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        1,  # mono
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    return header + b"\x00" * data_size


def assemble_video(
    segments: list[dict],
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    transition_duration: float = 0.5,
    use_ken_burns: bool = False,
) -> float:
    """Assemble segment images and audio into an MP4 video.

    Each segment dict must contain:
        - image_path: path to the source image
        - audio_path: path to a WAV audio file
        - audio_duration_seconds: duration of the audio clip
        - transition: one of "fade", "cut", "slide_left", "zoom_in"

    Args:
        segments: List of segment dictionaries.
        output_path: Where to write the output MP4.
        width: Output video width (default 1080).
        height: Output video height (default 1920).
        fps: Frames per second (default 30).
        transition_duration: Duration of transitions in seconds (default 0.5).

    Returns:
        Total video duration in seconds.

    Raises:
        VideoAssemblyError: If assembly fails.
    """
    if not segments:
        raise VideoAssemblyError("No segments provided")

    logger.info(f"Assembling video from {len(segments)} segments -> {output_path}")

    clips = []
    current_time = 0.0

    for i, seg in enumerate(segments):
        seg_duration = seg["audio_duration_seconds"]

        if use_ken_burns:
            image = _load_and_scale_image(seg["image_path"], width, height)
            motion = _pick_motion(i)
            frame_func = _make_ken_burns_frame_func(
                image, width, height, seg_duration, motion
            )
            video_clip = VideoClip(
                frame_function=frame_func,
                duration=seg_duration,
            ).with_fps(fps)
        else:
            # Static center-crop — much faster to encode
            img = Image.open(seg["image_path"]).convert("RGB")
            img = img.resize((width, height), Image.LANCZOS)
            static_frame = np.array(img)
            video_clip = VideoClip(
                frame_function=lambda t, f=static_frame: f,
                duration=seg_duration,
            ).with_fps(fps)

        # Attach audio
        audio_clip = AudioFileClip(seg["audio_path"])
        video_clip = video_clip.with_audio(audio_clip)

        video_clip = video_clip.with_start(current_time)
        clips.append(video_clip)
        current_time += seg_duration

        # Add a small silence gap between segments for natural pacing
        if i < len(segments) - 1:
            current_time += 0.3

    # Composite all clips together
    final = CompositeVideoClip(clips, size=(width, height))

    # Gentle audio fade-out at the end
    total_duration = final.duration
    fade_time = min(0.3, total_duration * 0.1)
    final = final.with_effects(
        [
            afx.AudioFadeOut(fade_time),
        ]
    )

    logger.info(f"Writing video: {total_duration:.1f}s, {width}x{height}, {fps}fps")

    final.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        pixel_format="yuv420p",
        temp_audiofile_path="/tmp/",
        logger=None,
    )

    # Clean up
    for clip in clips:
        clip.close()
    final.close()

    logger.info(f"Video written to {output_path} ({total_duration:.1f}s)")
    return total_duration
