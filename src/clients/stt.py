"""Client for the Speech-to-Text service (Nemotron Speech Streaming).

Transcribes audio files to text with optional word-level timestamps.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from src.settings import STT_URL

logger = logging.getLogger(__name__)

DEFAULT_STT_URL = STT_URL


class STTError(Exception):
    """Exception raised when speech-to-text fails."""

    pass


@dataclass
class WordTimestamp:
    """A single word with its start and end time in seconds."""

    word: str
    start: float
    end: float


@dataclass
class TranscriptionResult:
    """Result from a transcription request."""

    text: str
    words: list[WordTimestamp] | None


async def transcribe_audio(
    audio_bytes: bytes,
    timestamps: bool = True,
    filename: str = "audio.wav",
    stt_url: str = DEFAULT_STT_URL,
    max_retries: int = 3,
    timeout: float = 120.0,
) -> TranscriptionResult:
    """
    Transcribe audio bytes to text with optional word-level timestamps.

    Uses the file upload endpoint (POST /transcribe).

    Args:
        audio_bytes: Raw audio bytes (WAV, 16-bit PCM, mono, 16kHz recommended).
        timestamps: Whether to request word-level timestamps.
        filename: Filename hint for the upload.
        stt_url: Base URL of the STT service.
        max_retries: Maximum number of retry attempts.
        timeout: Request timeout in seconds.

    Returns:
        TranscriptionResult with text and optional word timestamps.

    Raises:
        STTError: If transcription fails after retries.
    """
    if not audio_bytes:
        raise STTError("Audio bytes cannot be empty")

    endpoint = f"{stt_url}/transcribe"
    params = {}
    if timestamps:
        params["timestamps"] = "true"

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(
                    f"Transcribing audio ({len(audio_bytes)} bytes, "
                    f"timestamps={timestamps})"
                )

                response = await client.post(
                    endpoint,
                    params=params,
                    files={"file": (filename, audio_bytes, "audio/wav")},
                )
                response.raise_for_status()

                data = response.json()
                text = data.get("text", "")

                words = None
                if timestamps and "words" in data:
                    words = [
                        WordTimestamp(
                            word=w["word"],
                            start=w["start"],
                            end=w["end"],
                        )
                        for w in data["words"]
                    ]

                logger.info(
                    f"Transcription complete: {len(text)} chars, "
                    f"{len(words) if words else 0} words"
                )
                return TranscriptionResult(text=text, words=words)

        except httpx.TimeoutException as e:
            logger.warning(f"STT request timeout (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
            else:
                raise STTError(
                    f"STT request timed out after {max_retries} attempts"
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"STT service HTTP error: {e.response.status_code}")
            raise STTError(f"STT service returned {e.response.status_code}")

        except httpx.RequestError as e:
            logger.warning(f"STT request error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
            else:
                raise STTError(f"Failed to connect to STT service: {e}")

    raise STTError("Transcription failed after all retries")


async def check_stt_health(
    stt_url: str = DEFAULT_STT_URL,
    timeout: float = 5.0,
) -> bool:
    """
    Check if the STT service is healthy.

    Args:
        stt_url: Base URL of the STT service.
        timeout: Request timeout in seconds.

    Returns:
        True if service is healthy, False otherwise.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{stt_url}/health")
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"STT health check failed: {e}")
        return False
