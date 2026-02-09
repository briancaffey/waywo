"""Client for the Text-to-Speech service (NVIDIA Magpie NIM).

Generates speech audio (WAV) from text using the TTS API.
"""

import asyncio
import logging
from typing import Optional

import httpx

from src.settings import TTS_URL

logger = logging.getLogger(__name__)

DEFAULT_TTS_URL = TTS_URL


class TTSError(Exception):
    """Exception raised when text-to-speech fails."""

    pass


async def generate_speech(
    text: str,
    language: str = "en-US",
    voice: Optional[str] = None,
    sample_rate_hz: int = 22050,
    encoding: str = "LINEAR_PCM",
    tts_url: str = DEFAULT_TTS_URL,
    max_retries: int = 3,
    timeout: float = 60.0,
) -> bytes:
    """
    Generate speech audio from text.

    Args:
        text: The text to synthesize into speech.
        language: Language code (e.g. "en-US").
        voice: Voice name (optional, uses service default if not set).
        sample_rate_hz: Audio sample rate in Hz.
        encoding: Audio encoding format.
        tts_url: Base URL of the TTS service.
        max_retries: Maximum number of retry attempts.
        timeout: Request timeout in seconds.

    Returns:
        Raw WAV audio bytes.

    Raises:
        TTSError: If speech generation fails after retries.
    """
    if not text:
        raise TTSError("Text cannot be empty")

    endpoint = f"{tts_url}/v1/audio/synthesize"

    data = {
        "text": text,
        "language": language,
        "sample_rate_hz": str(sample_rate_hz),
        "encoding": encoding,
    }
    if voice is not None:
        data["voice"] = voice

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(
                    f"Generating speech ({len(text)} chars, lang={language})"
                )

                response = await client.post(endpoint, data=data)
                response.raise_for_status()

                audio_bytes = response.content
                logger.info(
                    f"Speech generated: {len(audio_bytes)} bytes"
                )
                return audio_bytes

        except httpx.TimeoutException as e:
            logger.warning(f"TTS request timeout (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
            else:
                raise TTSError(
                    f"TTS request timed out after {max_retries} attempts"
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"TTS service HTTP error: {e.response.status_code}")
            raise TTSError(f"TTS service returned {e.response.status_code}")

        except httpx.RequestError as e:
            logger.warning(f"TTS request error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
            else:
                raise TTSError(f"Failed to connect to TTS service: {e}")

    raise TTSError("Speech generation failed after all retries")


async def list_voices(
    tts_url: str = DEFAULT_TTS_URL,
    timeout: float = 10.0,
) -> list[dict]:
    """
    List available voices from the TTS service.

    Args:
        tts_url: Base URL of the TTS service.
        timeout: Request timeout in seconds.

    Returns:
        List of voice dictionaries from the service.

    Raises:
        TTSError: If the request fails.
    """
    endpoint = f"{tts_url}/v1/audio/list_voices"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        raise TTSError(f"Failed to list voices: HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        raise TTSError(f"Failed to connect to TTS service: {e}")


async def check_tts_health(
    tts_url: str = DEFAULT_TTS_URL,
    timeout: float = 5.0,
) -> bool:
    """
    Check if the TTS service is healthy by listing voices.

    Args:
        tts_url: Base URL of the TTS service.
        timeout: Request timeout in seconds.

    Returns:
        True if service is healthy, False otherwise.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{tts_url}/v1/audio/list_voices")
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"TTS health check failed: {e}")
        return False
