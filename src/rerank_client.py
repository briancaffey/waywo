"""
Client for the rerank service.

The rerank service runs nvidia/llama-nemotron-rerank-1b-v2 model
and provides document reranking for RAG pipelines.
"""

import asyncio
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# Default rerank service configuration
DEFAULT_RERANK_URL = "http://192.168.5.173:8111"


class RerankError(Exception):
    """Exception raised when reranking fails."""

    pass


@dataclass
class RerankResult:
    """Result from the rerank service."""

    scores: list[float]
    ranked_indices: list[int]


async def rerank_documents(
    query: str,
    documents: list[str],
    rerank_url: str = DEFAULT_RERANK_URL,
    max_retries: int = 3,
    timeout: float = 60.0,
) -> RerankResult:
    """
    Rerank documents based on relevance to a query.

    Args:
        query: The search query
        documents: List of document texts to rerank
        rerank_url: Base URL of the rerank service
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds

    Returns:
        RerankResult with scores and ranked indices

    Raises:
        RerankError: If reranking fails after retries
    """
    if not documents:
        return RerankResult(scores=[], ranked_indices=[])

    if not query:
        raise RerankError("Query cannot be empty")

    endpoint = f"{rerank_url}/rerank"

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"📡 Calling rerank service for {len(documents)} document(s)")

                response = await client.post(
                    endpoint,
                    json={"query": query, "documents": documents},
                )
                response.raise_for_status()

                data = response.json()
                scores = data.get("scores", [])
                ranked_indices = data.get("ranked_indices", [])

                if len(scores) != len(documents):
                    raise RerankError(
                        f"Expected {len(documents)} scores, got {len(scores)}"
                    )

                logger.info(f"✅ Reranked {len(documents)} document(s)")
                return RerankResult(scores=scores, ranked_indices=ranked_indices)

        except httpx.TimeoutException as e:
            logger.warning(f"⏰ Rerank request timeout (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)  # Exponential backoff
            else:
                raise RerankError(
                    f"Rerank request timed out after {max_retries} attempts"
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Rerank service HTTP error: {e.response.status_code}")
            raise RerankError(f"Rerank service returned {e.response.status_code}")

        except httpx.RequestError as e:
            logger.warning(f"🔌 Rerank request error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
            else:
                raise RerankError(f"Failed to connect to rerank service: {e}")

        except Exception as e:
            logger.error(f"❌ Unexpected rerank error: {e}")
            raise RerankError(f"Reranking failed: {e}")

    raise RerankError("Reranking failed after all retries")


async def check_rerank_service_health(
    rerank_url: str = DEFAULT_RERANK_URL,
    timeout: float = 5.0,
) -> bool:
    """
    Check if the rerank service is healthy.

    Args:
        rerank_url: Base URL of the rerank service
        timeout: Request timeout in seconds

    Returns:
        True if service is healthy, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{rerank_url}/health")
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Rerank service health check failed: {e}")
        return False
