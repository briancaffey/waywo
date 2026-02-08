"""Tests for external service clients."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

import httpx

from src.clients.embedding import (
    EmbeddingError,
    blob_to_embedding,
    create_embedding_text,
    embedding_to_blob,
    get_embeddings,
    get_single_embedding,
    check_embedding_service_health,
)
from src.clients.rerank import (
    RerankError,
    RerankResult,
    rerank_documents,
    check_rerank_service_health,
)
from src.clients.firecrawl import (
    ScrapeResult,
    scrape_url,
    should_skip_url,
)
from src.clients.hn import fetch_item

# ---------------------------------------------------------------------------
# Embedding client tests
# ---------------------------------------------------------------------------


@pytest.mark.client
@pytest.mark.asyncio
async def test_get_embeddings():
    """get_embeddings returns embeddings from the service."""
    fake_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embeddings": fake_embeddings}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await get_embeddings(
            texts=["hello", "world"],
            embedding_url="http://fake:8000",
            max_retries=1,
        )

    assert result == fake_embeddings
    mock_client.post.assert_called_once()


@pytest.mark.client
@pytest.mark.asyncio
async def test_get_embeddings_empty_input():
    """get_embeddings returns empty list for empty input."""
    result = await get_embeddings(texts=[])
    assert result == []


@pytest.mark.client
@pytest.mark.asyncio
async def test_get_embeddings_timeout_retry():
    """get_embeddings retries on timeout."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.TimeoutException("timeout")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        pytest.raises(EmbeddingError, match="timed out"),
    ):
        await get_embeddings(
            texts=["hello"],
            embedding_url="http://fake:8000",
            max_retries=2,
        )

    # Should have retried
    assert mock_client.post.call_count == 2


@pytest.mark.client
@pytest.mark.asyncio
async def test_get_single_embedding():
    """get_single_embedding returns single embedding vector."""
    fake_embedding = [0.1, 0.2, 0.3]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embeddings": [fake_embedding]}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await get_single_embedding(
            text="hello",
            embedding_url="http://fake:8000",
            max_retries=1,
        )

    assert result == fake_embedding


@pytest.mark.client
def test_embedding_to_blob_roundtrip():
    """embedding_to_blob and blob_to_embedding are inverse operations."""
    original = [1.0, 2.0, -3.5, 0.0, 4.2]
    blob = embedding_to_blob(original)
    restored = blob_to_embedding(blob)

    assert len(restored) == len(original)
    for a, b in zip(original, restored):
        assert abs(a - b) < 1e-6


@pytest.mark.client
def test_create_embedding_text():
    """create_embedding_text combines title, description, hashtags."""
    result = create_embedding_text(
        title="Cool Project",
        description="A tool for testing.",
        hashtags=["python", "testing"],
    )
    assert "Cool Project" in result
    assert "A tool for testing." in result
    assert "#python" in result
    assert "#testing" in result


@pytest.mark.client
def test_create_embedding_text_no_hashtags():
    """create_embedding_text handles empty hashtags."""
    result = create_embedding_text(
        title="Project",
        description="Description.",
        hashtags=[],
    )
    assert result == "Project\nDescription."


@pytest.mark.client
@pytest.mark.asyncio
async def test_check_embedding_service_health_healthy():
    """check_embedding_service_health returns True when healthy."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await check_embedding_service_health("http://fake:8000")

    assert result is True


@pytest.mark.client
@pytest.mark.asyncio
async def test_check_embedding_service_health_down():
    """check_embedding_service_health returns False when service is down."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await check_embedding_service_health("http://fake:8000")

    assert result is False


# ---------------------------------------------------------------------------
# Rerank client tests
# ---------------------------------------------------------------------------


@pytest.mark.client
@pytest.mark.asyncio
async def test_rerank_documents():
    """rerank_documents returns ranked results."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "scores": [0.9, 0.7, 0.3],
        "ranked_indices": [0, 1, 2],
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await rerank_documents(
            query="test query",
            documents=["doc1", "doc2", "doc3"],
            rerank_url="http://fake:8111",
            max_retries=1,
        )

    assert isinstance(result, RerankResult)
    assert result.scores == [0.9, 0.7, 0.3]
    assert result.ranked_indices == [0, 1, 2]


@pytest.mark.client
@pytest.mark.asyncio
async def test_rerank_documents_empty():
    """rerank_documents returns empty result for empty documents."""
    result = await rerank_documents(
        query="test", documents=[], rerank_url="http://fake:8111"
    )
    assert result.scores == []
    assert result.ranked_indices == []


@pytest.mark.client
@pytest.mark.asyncio
async def test_rerank_documents_empty_query():
    """rerank_documents raises for empty query."""
    with pytest.raises(RerankError, match="Query cannot be empty"):
        await rerank_documents(
            query="", documents=["doc1"], rerank_url="http://fake:8111"
        )


@pytest.mark.client
@pytest.mark.asyncio
async def test_check_rerank_service_health():
    """check_rerank_service_health returns True when healthy."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await check_rerank_service_health("http://fake:8111")

    assert result is True


# ---------------------------------------------------------------------------
# Firecrawl client tests
# ---------------------------------------------------------------------------


@pytest.mark.client
@pytest.mark.parametrize(
    "url,should_skip_val,reason_contains",
    [
        ("", True, "empty_url"),
        ("javascript:void(0)", True, "invalid_scheme"),
        ("https://twitter.com/user", True, "skipped_domain"),
        ("https://youtube.com/watch?v=123", True, "skipped_domain"),
        ("https://example.com/file.pdf", True, "skipped_extension"),
        ("https://example.com/valid-page", False, ""),
    ],
)
def test_should_skip_url(url, should_skip_val, reason_contains):
    """should_skip_url filters out unwanted URLs."""
    skip, reason = should_skip_url(url)
    assert skip is should_skip_val
    if reason_contains:
        assert reason_contains in reason


@pytest.mark.client
@pytest.mark.asyncio
async def test_scrape_url_success():
    """scrape_url returns content on success."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "data": {
            "markdown": "# Page Title\nSome content here.",
            "metadata": {"title": "Page Title"},
        },
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await scrape_url(
            "https://example.com",
            max_retries=1,
            firecrawl_url="http://fake:3002",
        )

    assert isinstance(result, ScrapeResult)
    assert result.success is True
    assert "Page Title" in result.content


# ---------------------------------------------------------------------------
# HN client tests
# ---------------------------------------------------------------------------


@pytest.mark.client
def test_hn_fetch_item_success(sample_post_data):
    """fetch_item returns item data on success."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = sample_post_data

    with patch("requests.get", return_value=mock_response):
        result = fetch_item(12345)

    assert result == sample_post_data
    assert result["id"] == 12345


@pytest.mark.client
def test_hn_fetch_item_not_found():
    """fetch_item returns None for 404."""
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("requests.get", return_value=mock_response):
        result = fetch_item(99999)

    assert result is None


@pytest.mark.client
def test_hn_fetch_item_null_response():
    """fetch_item returns None when API returns null."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = None

    with patch("requests.get", return_value=mock_response):
        result = fetch_item(12345)

    assert result is None
