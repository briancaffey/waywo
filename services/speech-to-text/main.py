import base64
import logging
import tempfile
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

import nemo.collections.asr as nemo_asr
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
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


class TranscribeResponse(BaseModel):
    text: str


def transcribe_audio_file(audio_path: str) -> str:
    """Transcribe a single audio file and return the text."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        results = model.transcribe([audio_path])
        if isinstance(results, tuple):
            results = results[0]
        if not results:
            return ""
        result = results[0]
        # Handle Hypothesis objects from NeMo
        if hasattr(result, "text"):
            return result.text
        return str(result)
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
async def transcribe_upload(file: UploadFile = File(...)):
    """Transcribe an uploaded WAV audio file."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not file.filename or not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="Only WAV files are supported")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text = transcribe_audio_file(tmp_path)
        return TranscribeResponse(text=text)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/transcribe/base64", response_model=TranscribeResponse)
async def transcribe_base64(request: TranscribeBase64Request):
    """Transcribe base64-encoded WAV audio."""
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
        text = transcribe_audio_file(tmp_path)
        return TranscribeResponse(text=text)
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
