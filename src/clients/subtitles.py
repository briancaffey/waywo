"""Add animated word-level subtitles to videos using pycaps.

Extracts audio from an assembled video, transcribes it in one pass to get
word-level timestamps, then uses pycaps to render animated subtitles.
"""

import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from src.clients.stt import TranscriptionResult, transcribe_audio

logger = logging.getLogger(__name__)


class SubtitleError(Exception):
    """Exception raised when subtitle generation fails."""

    pass


# Custom CSS for subtitle styling — no template, built from scratch.
SUBTITLE_CSS = """\
.word {
    font-size: 24px;
    color: white;
    font-family: Arial, Helvetica, sans-serif;
    font-weight: 800;
    text-shadow: 0 2px 8px rgba(0,0,0,0.9), 0 0 2px rgba(0,0,0,0.5);
    text-transform: uppercase;
}
.word-being-narrated {
    color: #FFD700;
}
"""


def transcription_to_whisper_json(
    result: TranscriptionResult,
    pause_threshold: float = 0.25,
) -> dict:
    """Convert a TranscriptionResult to pycaps whisper_json format.

    Words are split into segments based on pauses in speech.  Pauses longer
    than *pause_threshold* seconds create segment boundaries, which naturally
    aligns with the silence gaps between narration segments in the assembled
    video.

    The whisper_json format expected by pycaps::

        {
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 0.5},
                        ...
                    ]
                }
            ]
        }
    """
    if not result.words:
        return {"segments": []}

    segments: list[dict] = []
    current_words = [result.words[0]]

    for i in range(1, len(result.words)):
        gap = result.words[i].start - result.words[i - 1].end
        if gap >= pause_threshold:
            segments.append(_words_to_segment(current_words))
            current_words = [result.words[i]]
        else:
            current_words.append(result.words[i])

    # Flush the last segment
    if current_words:
        segments.append(_words_to_segment(current_words))

    return {"segments": segments}


def _words_to_segment(words) -> dict:
    """Build a single whisper_json segment dict from a list of WordTimestamp."""
    return {
        "start": words[0].start,
        "end": words[-1].end,
        "words": [
            {"word": w.word, "start": w.start, "end": w.end} for w in words
        ],
    }


def extract_audio_to_wav(video_path: str | Path, wav_path: str | Path) -> None:
    """Extract audio from a video file to 16-kHz mono WAV using ffmpeg."""
    subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(wav_path),
            "-y",
        ],
        capture_output=True,
        check=True,
    )


def _run_pycaps_pipeline(
    video_path: str,
    output_path: str,
    whisper_json: dict,
) -> None:
    """Run the pycaps pipeline to burn subtitles onto a video.

    Uses a local template (copy of minimalist with animations removed)
    and layers custom CSS on top.

    This function is **synchronous** — call it via ``run_in_executor``
    from async code.
    """
    from pycaps import TemplateLoader, TranscriptFormat

    builder = TemplateLoader("src/clients/subtitle-template").with_input_video(video_path).load(False)
    builder.with_output_video(output_path)
    builder.with_transcription(whisper_json, TranscriptFormat.WHISPER_JSON)
    builder.add_css_content(SUBTITLE_CSS)

    pipeline = builder.build()
    pipeline.run()


async def add_subtitles(
    video_path: str | Path,
    output_path: str | Path,
    stt_url: str | None = None,
) -> Path:
    """Add word-level animated subtitles to a video.

    1. Extracts audio from the assembled video to a temp WAV file
    2. Transcribes the full audio in one STT pass
    3. Converts word timestamps to whisper_json format
    4. Burns subtitles onto the video using pycaps

    Args:
        video_path: Path to the input video (MP4).
        output_path: Where to write the subtitled video.
        stt_url: Optional STT service URL override.

    Returns:
        Path to the output video with subtitles.

    Raises:
        SubtitleError: If subtitle generation fails.
    """
    video_path = Path(video_path)
    output_path = Path(output_path)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)

    try:
        # 1. Extract audio from the assembled video
        logger.info(f"Extracting audio from {video_path}")
        extract_audio_to_wav(video_path, wav_path)

        # 2. Transcribe the full audio in one pass
        audio_bytes = wav_path.read_bytes()
        stt_kwargs: dict = {"audio_bytes": audio_bytes, "timestamps": True}
        if stt_url:
            stt_kwargs["stt_url"] = stt_url

        logger.info("Transcribing full video audio for subtitles")
        result = await transcribe_audio(**stt_kwargs)

        # 3. Convert to whisper_json
        whisper_json = transcription_to_whisper_json(result)
        word_count = sum(len(s["words"]) for s in whisper_json["segments"])
        logger.info(f"Transcription: {word_count} words across {len(whisper_json['segments'])} segments")

        if word_count == 0:
            logger.warning("No words transcribed — copying video without subtitles")
            shutil.copy2(video_path, output_path)
            return output_path

        # 4. Run pycaps (synchronous — offload to thread pool)
        logger.info(f"Rendering subtitles -> {output_path}")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            _run_pycaps_pipeline,
            str(video_path),
            str(output_path),
            whisper_json,
        )

        logger.info(f"Subtitled video written to {output_path}")
        return output_path

    except Exception as e:
        raise SubtitleError(f"Failed to add subtitles: {e}") from e

    finally:
        wav_path.unlink(missing_ok=True)
