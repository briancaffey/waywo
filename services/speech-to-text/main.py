import base64
import io
import logging
import tempfile
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

import nemo.collections.asr as nemo_asr
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model: nemo_asr.models.ASRModel | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    model = nemo_asr.models.ASRModel.from_pretrained(
        model_name="nvidia/nemotron-speech-streaming-en-0.6b"
    )
    yield
    model = None


app = FastAPI(
    title="Speech-to-Text Service",
    description="Microservice for transcribing audio using nvidia/nemotron-speech-streaming-en-0.6b",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


class TranscribeBase64Request(BaseModel):
    audio_base64: str
    timestamps: bool = False


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class TranscribeResponse(BaseModel):
    text: str
    words: list[WordTimestamp] | None = None


def transcribe_audio_file(audio_path: str, timestamps: bool = False) -> dict:
    """Transcribe a single audio file and return the text and optional word timestamps."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        results = model.transcribe([audio_path], timestamps=timestamps)
        if isinstance(results, tuple):
            results = results[0]
        if not results:
            return {"text": "", "words": None}
        result = results[0]

        text = result.text if hasattr(result, "text") else str(result)

        words = None
        if timestamps and hasattr(result, "timestamp") and result.timestamp:
            word_ts = result.timestamp.get("word", [])
            words = [
                {"word": w["word"], "start": w["start"], "end": w["end"]}
                for w in word_ts
            ]

        return {"text": text, "words": words}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


async def stream_transcription(audio_path: str):
    """Stream transcription results using cache-aware streaming."""
    try:
        if model is None:
            yield f"data: ERROR: Model not loaded\n\n"
            return

        # Try streaming transcription first
        try:
            has_generator = hasattr(model, "transcribe_generator")
            if has_generator:
                for partial_result in model.transcribe_generator(
                    audio=[audio_path],
                    override_config=None,
                ):
                    if partial_result:
                        text = partial_result[0] if isinstance(partial_result, list) else partial_result
                        if hasattr(text, "text"):
                            text = text.text
                        yield f"data: {text}\n\n"
            else:
                raise AttributeError("No transcribe_generator")
        except (AttributeError, TypeError):
            # Fallback if transcribe_generator not available - do full transcription
            results = model.transcribe([audio_path])
            if isinstance(results, tuple):
                results = results[0]
            if results:
                result = results[0]
                if hasattr(result, "text"):
                    result = result.text
                yield f"data: {result}\n\n"

        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"data: ERROR: {str(e)}\n\n"
    finally:
        # Clean up temp file
        Path(audio_path).unlink(missing_ok=True)


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_upload(file: UploadFile = File(...), timestamps: bool = False):
    """Transcribe an uploaded WAV audio file. Set timestamps=true for word-level timing."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not file.filename or not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="Only WAV files are supported")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = transcribe_audio_file(tmp_path, timestamps=timestamps)
        return TranscribeResponse(**result)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/transcribe/base64", response_model=TranscribeResponse)
async def transcribe_base64(request: TranscribeBase64Request):
    """Transcribe base64-encoded WAV audio. Set timestamps=true in the request body for word-level timing."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        audio_bytes = base64.b64decode(request.audio_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        result = transcribe_audio_file(tmp_path, timestamps=request.timestamps)
        return TranscribeResponse(**result)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/transcribe/stream")
async def transcribe_stream_upload(file: UploadFile = File(...)):
    """Transcribe an uploaded WAV file with streaming SSE responses."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not file.filename or not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="Only WAV files are supported")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    return StreamingResponse(
        stream_transcription(tmp_path),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.post("/transcribe/stream/base64")
async def transcribe_stream_base64(request: TranscribeBase64Request):
    """Transcribe base64-encoded WAV audio with streaming SSE responses."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        audio_bytes = base64.b64decode(request.audio_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    return StreamingResponse(
        stream_transcription(tmp_path),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": model is not None}


def create_wav_header(sample_rate: int, num_samples: int) -> bytes:
    """Create a WAV header for 16-bit mono PCM audio."""
    data_size = num_samples * 2
    header = io.BytesIO()
    # RIFF header
    header.write(b'RIFF')
    header.write((36 + data_size).to_bytes(4, 'little'))
    header.write(b'WAVE')
    # fmt chunk
    header.write(b'fmt ')
    header.write((16).to_bytes(4, 'little'))  # chunk size
    header.write((1).to_bytes(2, 'little'))   # PCM format
    header.write((1).to_bytes(2, 'little'))   # mono
    header.write(sample_rate.to_bytes(4, 'little'))
    header.write((sample_rate * 2).to_bytes(4, 'little'))  # byte rate
    header.write((2).to_bytes(2, 'little'))   # block align
    header.write((16).to_bytes(2, 'little'))  # bits per sample
    # data chunk
    header.write(b'data')
    header.write(data_size.to_bytes(4, 'little'))
    return header.getvalue()


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """Real-time transcription via WebSocket."""
    logger.info("WebSocket: New connection")
    await websocket.accept()
    logger.info("WebSocket: Connection accepted")

    if model is None:
        logger.error("WebSocket: Model not loaded")
        await websocket.send_json({"error": "Model not loaded"})
        await websocket.close()
        return

    # Buffer for raw PCM samples (16-bit signed integers)
    pcm_buffer = bytearray()
    sample_rate = 16000
    last_text = ""
    chunk_count = 0

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                logger.info("WebSocket: Client disconnected")
                break

            if "text" in message:
                text = message["text"]
                logger.info(f"WebSocket: Received text message: {text}")

                if text == "END":
                    logger.info(f"WebSocket: END received, buffer has {len(pcm_buffer)} bytes")
                    if len(pcm_buffer) > 0:
                        text_result = await transcribe_pcm_buffer(pcm_buffer, sample_rate)
                        logger.info(f"WebSocket: Final transcription: {text_result}")
                        await websocket.send_json({"text": text_result, "final": True})
                    break

            elif "bytes" in message:
                chunk = message["bytes"]
                chunk_count += 1
                pcm_buffer.extend(chunk)

                # Log every 10 chunks to avoid spam
                if chunk_count % 10 == 0:
                    logger.info(f"WebSocket: Received {chunk_count} chunks, buffer: {len(pcm_buffer)} bytes")

                # Transcribe every ~2 seconds of audio (16000 samples/sec * 2 bytes * 2 sec)
                if len(pcm_buffer) >= sample_rate * 2 * 2:
                    logger.info(f"WebSocket: Transcribing {len(pcm_buffer)} bytes of audio...")
                    text_result = await transcribe_pcm_buffer(pcm_buffer, sample_rate)

                    if text_result and text_result != last_text:
                        logger.info(f"WebSocket: Partial result: {text_result}")
                        last_text = text_result
                        await websocket.send_json({"text": text_result, "final": False})

    except Exception as e:
        logger.error(f"WebSocket: Error - {e}", exc_info=True)
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        logger.info("WebSocket: Closing connection")


async def transcribe_pcm_buffer(pcm_buffer: bytearray, sample_rate: int) -> str:
    """Transcribe PCM audio buffer."""
    if model is None or len(pcm_buffer) == 0:
        return ""

    # Create WAV file with header + PCM data
    num_samples = len(pcm_buffer) // 2
    wav_header = create_wav_header(sample_rate, num_samples)
    wav_data = wav_header + bytes(pcm_buffer)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_data)
        tmp_path = tmp.name

    try:
        results = model.transcribe([tmp_path])
        if isinstance(results, tuple):
            results = results[0]
        if results:
            result = results[0]
            if hasattr(result, "text"):
                return result.text
            return str(result)
        return ""
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return ""
    finally:
        Path(tmp_path).unlink(missing_ok=True)
