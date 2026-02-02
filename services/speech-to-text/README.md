# Speech-to-Text Service

A FastAPI microservice for speech-to-text transcription using the `nvidia/nemotron-speech-streaming-en-0.6b` model.

See [nvidia/nemotron-speech-streaming-en-0.6b](https://huggingface.co/nvidia/nemotron-speech-streaming-en-0.6b) for model details.

## Installation

```bash
cd services/speech-to-text
uv sync
```

## Running the Service

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8001
```

For development with auto-reload:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## Web UI

Open http://localhost:8001/ in your browser for an interactive testing interface that supports:

- File upload transcription
- Base64 audio transcription
- Streaming transcription
- Microphone recording and transcription

## API Endpoints

### Health Check

```bash
curl http://localhost:8001/health
```

### Transcribe Audio (File Upload)

```bash
curl -X POST http://localhost:8001/transcribe \
  -F "file=@audio.wav"
```

Response:

```json
{
  "text": "transcribed text here"
}
```

### Transcribe Audio (Base64)

```bash
curl -X POST http://localhost:8001/transcribe/base64 \
  -H "Content-Type: application/json" \
  -d '{"audio_base64": "<base64-encoded-wav>"}'
```

### Streaming Transcription (File Upload)

```bash
curl -N -X POST http://localhost:8001/transcribe/stream \
  -F "file=@audio.wav"
```

Returns Server-Sent Events:

```
data: partial transcription
data: more text
data: [DONE]
```

### Streaming Transcription (Base64)

```bash
curl -N -X POST http://localhost:8001/transcribe/stream/base64 \
  -H "Content-Type: application/json" \
  -d '{"audio_base64": "<base64-encoded-wav>"}'
```

## API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## Supported Formats

- WAV audio files only
