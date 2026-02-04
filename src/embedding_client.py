"""
Client for the embedding service.

The embedding service runs nvidia/llama-embed-nemotron-8b model
and provides vector embeddings for text documents.
"""

import asyncio
import logging
import struct
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Default embedding service configuration
DEFAULT_EMBEDDING_URL = "http://192.168.5.96:8000"
EMBEDDING_DIMENSION = 4096  # llama-embed-nemotron-8b output dimension


class EmbeddingError(Exception):
    """Exception raised when embedding generation fails."""

    pass


async def get_embeddings(
    texts: list[str],
    embedding_url: str = DEFAULT_EMBEDDING_URL,
    max_retries: int = 3,
    timeout: float = 60.0,
) -> list[list[float]]:
    """
    Get embeddings for a list of texts from the embedding service.

    Args:
        texts: List of text documents to embed
        embedding_url: Base URL of the embedding service
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds

    Returns:
        List of embedding vectors (each is a list of floats)

    Raises:
        EmbeddingError: If embedding generation fails after retries
    """
    if not texts:
        return []

    endpoint = f"{embedding_url}/embed"

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"📡 Calling embedding service for {len(texts)} text(s)")

                response = await client.post(
                    endpoint,
                    json={"documents": texts},
                )
                response.raise_for_status()

                data = response.json()
                embeddings = data.get("embeddings", [])

                if len(embeddings) != len(texts):
                    raise EmbeddingError(
                        f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                    )

                logger.info(f"✅ Got {len(embeddings)} embedding(s)")
                return embeddings

        except httpx.TimeoutException as e:
            logger.warning(f"⏰ Embedding request timeout (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)  # Exponential backoff
            else:
                raise EmbeddingError(f"Embedding request timed out after {max_retries} attempts")

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Embedding service HTTP error: {e.response.status_code}")
            raise EmbeddingError(f"Embedding service returned {e.response.status_code}")

        except httpx.RequestError as e:
            logger.warning(f"🔌 Embedding request error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
            else:
                raise EmbeddingError(f"Failed to connect to embedding service: {e}")

        except Exception as e:
            logger.error(f"❌ Unexpected embedding error: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")

    raise EmbeddingError("Embedding generation failed after all retries")


async def get_single_embedding(
    text: str,
    embedding_url: str = DEFAULT_EMBEDDING_URL,
    max_retries: int = 3,
    timeout: float = 60.0,
) -> list[float]:
    """
    Get embedding for a single text document.

    Args:
        text: Text document to embed
        embedding_url: Base URL of the embedding service
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds

    Returns:
        Embedding vector as a list of floats

    Raises:
        EmbeddingError: If embedding generation fails
    """
    embeddings = await get_embeddings(
        texts=[text],
        embedding_url=embedding_url,
        max_retries=max_retries,
        timeout=timeout,
    )
    return embeddings[0]


def embedding_to_blob(embedding: list[float]) -> bytes:
    """
    Convert an embedding (list of floats) to a binary blob for SQLite storage.

    Uses little-endian 32-bit floats (FLOAT32) format compatible with sqlite-vector.

    Args:
        embedding: List of float values

    Returns:
        Binary blob representation
    """
    return struct.pack(f"<{len(embedding)}f", *embedding)


def blob_to_embedding(blob: bytes) -> list[float]:
    """
    Convert a binary blob back to an embedding (list of floats).

    Args:
        blob: Binary blob from SQLite

    Returns:
        List of float values
    """
    num_floats = len(blob) // 4  # 4 bytes per float32
    return list(struct.unpack(f"<{num_floats}f", blob))


def create_embedding_text(
    title: str,
    description: str,
    hashtags: list[str],
) -> str:
    """
    Create the combined text for embedding from project fields.

    Args:
        title: Project title
        description: Project description
        hashtags: List of hashtag strings

    Returns:
        Combined text suitable for embedding
    """
    hashtag_str = " ".join(f"#{tag}" for tag in hashtags) if hashtags else ""
    return f"{title}\n{description}\n{hashtag_str}".strip()


async def check_embedding_service_health(
    embedding_url: str = DEFAULT_EMBEDDING_URL,
    timeout: float = 5.0,
) -> bool:
    """
    Check if the embedding service is healthy.

    Args:
        embedding_url: Base URL of the embedding service
        timeout: Request timeout in seconds

    Returns:
        True if service is healthy, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{embedding_url}/health")
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Embedding service health check failed: {e}")
        return False
