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

Open http://localhost:8001/ in your browser for an interactive testing interface that supports all API endpoints including real-time live transcription from your microphone.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web UI |
| `/health` | GET | Health check |
| `/transcribe` | POST | Transcribe uploaded WAV file |
| `/transcribe/base64` | POST | Transcribe base64-encoded WAV |
| `/transcribe/stream` | POST | Streaming SSE transcription (file upload) |
| `/transcribe/stream/base64` | POST | Streaming SSE transcription (base64) |
| `/ws/transcribe` | WebSocket | Real-time live transcription |

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

### Real-time Live Transcription (WebSocket)

Connect to the WebSocket endpoint for live microphone transcription with instant feedback as you speak:

```
ws://localhost:8001/ws/transcribe
```

**Protocol:**

1. Connect to the WebSocket endpoint
2. Send raw PCM audio data as binary messages (16-bit signed integers, mono, 16kHz)
3. Receive JSON messages with partial transcriptions:
   ```json
   {"text": "transcribed text so far", "final": false}
   ```
4. Send `END` as a text message to signal end of recording
5. Receive final transcription:
   ```json
   {"text": "complete transcription", "final": true}
   ```

**JavaScript Example:**

```javascript
const ws = new WebSocket('ws://localhost:8001/ws/transcribe');
const audioContext = new AudioContext({ sampleRate: 16000 });

// Get microphone stream and send PCM chunks
navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);

  processor.onaudioprocess = (e) => {
    const float32 = e.inputBuffer.getChannelData(0);
    const int16 = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      int16[i] = Math.max(-1, Math.min(1, float32[i])) * 0x7FFF;
    }
    ws.send(int16.buffer);
  };

  source.connect(processor);
  processor.connect(audioContext.destination);
});

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.final ? 'Final:' : 'Partial:', data.text);
};
```

## API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## Supported Formats

- WAV audio files (16-bit PCM, mono, 16kHz recommended)
