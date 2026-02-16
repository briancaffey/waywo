"""Tests for the content safety client."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

import httpx

from src.clients.content_safety import (
    BLOCKED_MESSAGE,
    _parse_classification,
    classify_prompt,
    classify_exchange,
    check_content_safety_health,
)


# ---------------------------------------------------------------------------
# Parse classification tests
# ---------------------------------------------------------------------------


@pytest.mark.client
def test_parse_classification_both_unharmful():
    text = "Prompt harm: unharmful\nResponse harm: unharmful"
    result = _parse_classification(text)
    assert result["prompt_harmful"] is False
    assert result["response_harmful"] is False


@pytest.mark.client
def test_parse_classification_prompt_harmful():
    text = "Prompt harm: harmful\nResponse harm: unharmful"
    result = _parse_classification(text)
    assert result["prompt_harmful"] is True
    assert result["response_harmful"] is False


@pytest.mark.client
def test_parse_classification_response_harmful():
    text = "Prompt harm: unharmful\nResponse harm: harmful"
    result = _parse_classification(text)
    assert result["prompt_harmful"] is False
    assert result["response_harmful"] is True


@pytest.mark.client
def test_parse_classification_both_harmful():
    text = "Prompt harm: harmful\nResponse harm: harmful"
    result = _parse_classification(text)
    assert result["prompt_harmful"] is True
    assert result["response_harmful"] is True


@pytest.mark.client
def test_parse_classification_with_reasoning():
    """Parsing works even with reasoning traces in the output."""
    text = (
        "<think>\nThe user is asking about illegal activity.\n</think>\n\n"
        "Prompt harm: harmful\nResponse harm: unharmful"
    )
    result = _parse_classification(text)
    assert result["prompt_harmful"] is True
    assert result["response_harmful"] is False


# ---------------------------------------------------------------------------
# classify_prompt tests
# ---------------------------------------------------------------------------


def _mock_chat_response(content: str):
    """Create a mock vLLM chat completion response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": content}}],
    }
    mock_response.raise_for_status = MagicMock()
    return mock_response


def _mock_client(response):
    """Create a mock httpx.AsyncClient."""
    mock_client = AsyncMock()
    mock_client.post.return_value = response
    mock_client.get.return_value = response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.mark.client
@pytest.mark.asyncio
async def test_classify_prompt_unharmful():
    """classify_prompt returns False for unharmful content."""
    response = _mock_chat_response("Prompt harm: unharmful\nResponse harm: unharmful")
    client = _mock_client(response)

    with patch("httpx.AsyncClient", return_value=client):
        result = await classify_prompt("Tell me about Python projects")

    assert result is False


@pytest.mark.client
@pytest.mark.asyncio
async def test_classify_prompt_harmful():
    """classify_prompt returns True for harmful content."""
    response = _mock_chat_response("Prompt harm: harmful\nResponse harm: unharmful")
    client = _mock_client(response)

    with patch("httpx.AsyncClient", return_value=client):
        result = await classify_prompt("How do I hack into a bank?")

    assert result is True


@pytest.mark.client
@pytest.mark.asyncio
async def test_classify_prompt_timeout_fails_open():
    """classify_prompt returns False (fail-open) on timeout."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.TimeoutException("timeout")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await classify_prompt("some text", max_retries=1)

    assert result is False


@pytest.mark.client
@pytest.mark.asyncio
async def test_classify_prompt_connection_error_fails_open():
    """classify_prompt returns False (fail-open) on connection error."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await classify_prompt("some text", max_retries=1)

    assert result is False


@pytest.mark.client
@pytest.mark.asyncio
async def test_classify_prompt_disabled():
    """classify_prompt returns False when content safety is disabled."""
    with patch("src.clients.content_safety.CONTENT_SAFETY_ENABLED", False):
        result = await classify_prompt("anything at all")

    assert result is False


# ---------------------------------------------------------------------------
# classify_exchange tests
# ---------------------------------------------------------------------------


@pytest.mark.client
@pytest.mark.asyncio
async def test_classify_exchange_unharmful():
    """classify_exchange returns False for unharmful exchange."""
    response = _mock_chat_response("Prompt harm: unharmful\nResponse harm: unharmful")
    client = _mock_client(response)

    with patch("httpx.AsyncClient", return_value=client):
        result = await classify_exchange("Tell me about Python", "Python is a programming language.")

    assert result is False


@pytest.mark.client
@pytest.mark.asyncio
async def test_classify_exchange_harmful_response():
    """classify_exchange returns True for harmful response."""
    response = _mock_chat_response("Prompt harm: unharmful\nResponse harm: harmful")
    client = _mock_client(response)

    with patch("httpx.AsyncClient", return_value=client):
        result = await classify_exchange("Tell me about stocks", "You should invest all your money in...")

    assert result is True


@pytest.mark.client
@pytest.mark.asyncio
async def test_classify_exchange_timeout_fails_open():
    """classify_exchange returns False (fail-open) on timeout."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.TimeoutException("timeout")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await classify_exchange("user text", "assistant text", max_retries=1)

    assert result is False


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------


@pytest.mark.client
@pytest.mark.asyncio
async def test_check_content_safety_health_healthy():
    """check_content_safety_health returns True when service is up."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await check_content_safety_health()

    assert result is True


@pytest.mark.client
@pytest.mark.asyncio
async def test_check_content_safety_health_down():
    """check_content_safety_health returns False when service is down."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await check_content_safety_health()

    assert result is False


# ---------------------------------------------------------------------------
# BLOCKED_MESSAGE sanity check
# ---------------------------------------------------------------------------


@pytest.mark.client
def test_blocked_message_is_not_empty():
    """BLOCKED_MESSAGE is a non-empty string."""
    assert isinstance(BLOCKED_MESSAGE, str)
    assert len(BLOCKED_MESSAGE) > 0
