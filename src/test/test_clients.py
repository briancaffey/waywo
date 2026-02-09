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
from src.clients.invokeai import (
    InvokeAIError,
    GeneratedImage,
    generate_image,
    check_invokeai_health,
    _build_txt2img_batch,
    _build_ref_img_batch,
)
from src.clients.tts import (
    TTSError,
    generate_speech,
    list_voices,
    check_tts_health,
)
from src.clients.stt import (
    STTError,
    WordTimestamp,
    TranscriptionResult,
    transcribe_audio,
    check_stt_health,
)

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


# ---------------------------------------------------------------------------
# InvokeAI client tests
# ---------------------------------------------------------------------------


@pytest.mark.client
def test_build_txt2img_batch():
    """_build_txt2img_batch creates a valid batch payload."""
    batch = _build_txt2img_batch(
        prompt="a red cat",
        width=512,
        height=768,
        num_steps=8,
        seed=42,
    )

    assert batch["queue_id"] == "default"
    graph = batch["batch"]["graph"]

    # Check prompt was set
    prompt_node = graph["nodes"]["positive_prompt:CjR0mYpz31"]
    assert prompt_node["value"] == "a red cat"

    # Check seed was set
    seed_node = graph["nodes"]["seed:B3us1QPx5h"]
    assert seed_node["value"] == 42

    # Check dimensions and steps on denoise node
    denoise_node = graph["nodes"]["flux2_denoise:oTqFW3KTNk"]
    assert denoise_node["width"] == 512
    assert denoise_node["height"] == 768
    assert denoise_node["num_steps"] == 8

    # Check dimensions and steps on metadata node
    metadata_node = graph["nodes"]["core_metadata:azr5jlV6MZ"]
    assert metadata_node["width"] == 512
    assert metadata_node["height"] == 768
    assert metadata_node["steps"] == 8


@pytest.mark.client
def test_build_ref_img_batch():
    """_build_ref_img_batch creates a valid batch payload with reference image."""
    batch = _build_ref_img_batch(
        prompt="cartoon style",
        reference_image_name="test-image-123.png",
        width=1024,
        height=1024,
        num_steps=16,
        seed=99,
    )

    graph = batch["batch"]["graph"]

    # Check prompt was set
    prompt_node = graph["nodes"]["positive_prompt:DpqaYB9S7t"]
    assert prompt_node["value"] == "cartoon style"

    # Check reference image was set on kontext node
    kontext_node = graph["nodes"]["flux_kontext:HYkcPvWDua"]
    assert kontext_node["image"]["image_name"] == "test-image-123.png"

    # Check ref_images in metadata
    metadata_node = graph["nodes"]["core_metadata:pxJjogXVaB"]
    assert len(metadata_node["ref_images"]) == 1
    ref_img = metadata_node["ref_images"][0]
    assert (
        ref_img["config"]["image"]["original"]["image"]["image_name"]
        == "test-image-123.png"
    )


@pytest.mark.client
@pytest.mark.asyncio
async def test_generate_image_success():
    """generate_image returns a GeneratedImage on success."""
    # Mock the three stages: submit -> poll -> extract -> download

    # 1. Submit batch response
    submit_response = MagicMock()
    submit_response.status_code = 200
    submit_response.json.return_value = {
        "batch": {"batch_id": "batch-123"},
        "item_ids": [1],
        "queue_id": "default",
    }
    submit_response.raise_for_status = MagicMock()

    # 2. Batch status response (completed)
    status_response = MagicMock()
    status_response.status_code = 200
    status_response.json.return_value = {
        "completed": 1,
        "failed": 0,
        "total": 1,
    }

    # 3. Queue item response (with image result)
    item_response = MagicMock()
    item_response.status_code = 200
    item_response.json.return_value = {
        "session": {
            "results": {
                "canvas_output:rHGkBPcPOE": {
                    "type": "image_output",
                    "image": {"image_name": "generated-abc.png"},
                    "width": 1024,
                    "height": 1024,
                }
            }
        }
    }

    # 4. Download response
    download_response = MagicMock()
    download_response.status_code = 200
    download_response.content = b"fake-image-bytes"

    mock_client = AsyncMock()
    # First call: POST (submit), then GET (status), GET (item), GET (download)
    mock_client.post.return_value = submit_response
    mock_client.get.side_effect = [status_response, item_response, download_response]
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await generate_image(
            prompt="a blue sky",
            width=1024,
            height=1024,
            seed=42,
            invokeai_url="http://fake:9090",
            max_retries=1,
        )

    assert isinstance(result, GeneratedImage)
    assert result.image_name == "generated-abc.png"
    assert result.image_bytes == b"fake-image-bytes"
    assert result.width == 1024
    assert result.height == 1024


@pytest.mark.client
@pytest.mark.asyncio
async def test_generate_image_batch_failure():
    """generate_image raises InvokeAIError when batch fails."""
    # Submit succeeds
    submit_response = MagicMock()
    submit_response.status_code = 200
    submit_response.json.return_value = {
        "batch": {"batch_id": "batch-fail"},
        "item_ids": [1],
        "queue_id": "default",
    }
    submit_response.raise_for_status = MagicMock()

    # Status shows failure
    status_response = MagicMock()
    status_response.status_code = 200
    status_response.json.return_value = {
        "completed": 0,
        "failed": 1,
        "total": 1,
    }

    mock_client = AsyncMock()
    mock_client.post.return_value = submit_response
    mock_client.get.return_value = status_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        pytest.raises(InvokeAIError, match="failed"),
    ):
        await generate_image(
            prompt="a blue sky",
            seed=42,
            invokeai_url="http://fake:9090",
            max_retries=1,
        )


@pytest.mark.client
@pytest.mark.asyncio
async def test_check_invokeai_health_healthy():
    """check_invokeai_health returns True when service is up."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await check_invokeai_health("http://fake:9090")

    assert result is True


@pytest.mark.client
@pytest.mark.asyncio
async def test_check_invokeai_health_down():
    """check_invokeai_health returns False when service is down."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await check_invokeai_health("http://fake:9090")

    assert result is False


# ---------------------------------------------------------------------------
# TTS client tests
# ---------------------------------------------------------------------------


@pytest.mark.client
@pytest.mark.asyncio
async def test_generate_speech_success():
    """generate_speech returns WAV bytes on success."""
    fake_wav = b"RIFF\x00\x00\x00\x00WAVEfmt fake-audio-data"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = fake_wav
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await generate_speech(
            text="Hello world",
            tts_url="http://fake:9000",
            max_retries=1,
        )

    assert result == fake_wav
    mock_client.post.assert_called_once()
    # Verify multipart form data was sent (not JSON)
    call_kwargs = mock_client.post.call_args
    assert (
        call_kwargs.kwargs.get("data") is not None
        or call_kwargs[1].get("data") is not None
    )


@pytest.mark.client
@pytest.mark.asyncio
async def test_generate_speech_empty_text():
    """generate_speech raises TTSError for empty text."""
    with pytest.raises(TTSError, match="Text cannot be empty"):
        await generate_speech(text="", tts_url="http://fake:9000")


@pytest.mark.client
@pytest.mark.asyncio
async def test_generate_speech_timeout_retry():
    """generate_speech retries on timeout."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.TimeoutException("timeout")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        pytest.raises(TTSError, match="timed out"),
    ):
        await generate_speech(
            text="Hello",
            tts_url="http://fake:9000",
            max_retries=2,
        )

    assert mock_client.post.call_count == 2


@pytest.mark.client
@pytest.mark.asyncio
async def test_list_voices_success():
    """list_voices returns voice list on success."""
    fake_voices = [{"name": "English-US.Female-1"}, {"name": "English-US.Male-1"}]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = fake_voices
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await list_voices(tts_url="http://fake:9000")

    assert result == fake_voices
    assert len(result) == 2


@pytest.mark.client
@pytest.mark.asyncio
async def test_check_tts_health_healthy():
    """check_tts_health returns True when service is up."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await check_tts_health("http://fake:9000")

    assert result is True


@pytest.mark.client
@pytest.mark.asyncio
async def test_check_tts_health_down():
    """check_tts_health returns False when service is down."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await check_tts_health("http://fake:9000")

    assert result is False


# ---------------------------------------------------------------------------
# STT client tests
# ---------------------------------------------------------------------------


@pytest.mark.client
@pytest.mark.asyncio
async def test_transcribe_audio_success():
    """transcribe_audio returns TranscriptionResult on success."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "text": "hello world",
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await transcribe_audio(
            audio_bytes=b"fake-audio-data",
            timestamps=False,
            stt_url="http://fake:8001",
            max_retries=1,
        )

    assert isinstance(result, TranscriptionResult)
    assert result.text == "hello world"
    assert result.words is None


@pytest.mark.client
@pytest.mark.asyncio
async def test_transcribe_audio_with_timestamps():
    """transcribe_audio parses word-level timestamps."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "text": "hello world",
        "words": [
            {"word": "hello", "start": 0.0, "end": 0.32},
            {"word": "world", "start": 0.35, "end": 0.72},
        ],
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await transcribe_audio(
            audio_bytes=b"fake-audio-data",
            timestamps=True,
            stt_url="http://fake:8001",
            max_retries=1,
        )

    assert isinstance(result, TranscriptionResult)
    assert result.text == "hello world"
    assert result.words is not None
    assert len(result.words) == 2
    assert result.words[0].word == "hello"
    assert result.words[0].start == 0.0
    assert result.words[0].end == 0.32
    assert result.words[1].word == "world"
    assert result.words[1].start == 0.35
    assert result.words[1].end == 0.72


@pytest.mark.client
@pytest.mark.asyncio
async def test_transcribe_audio_empty_bytes():
    """transcribe_audio raises STTError for empty audio."""
    with pytest.raises(STTError, match="Audio bytes cannot be empty"):
        await transcribe_audio(audio_bytes=b"", stt_url="http://fake:8001")


@pytest.mark.client
@pytest.mark.asyncio
async def test_transcribe_audio_timeout_retry():
    """transcribe_audio retries on timeout."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.TimeoutException("timeout")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        pytest.raises(STTError, match="timed out"),
    ):
        await transcribe_audio(
            audio_bytes=b"fake-audio",
            stt_url="http://fake:8001",
            max_retries=2,
        )

    assert mock_client.post.call_count == 2


@pytest.mark.client
@pytest.mark.asyncio
async def test_check_stt_health_healthy():
    """check_stt_health returns True when service is up."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await check_stt_health("http://fake:8001")

    assert result is True


@pytest.mark.client
@pytest.mark.asyncio
async def test_check_stt_health_down():
    """check_stt_health returns False when service is down."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await check_stt_health("http://fake:8001")

    assert result is False
