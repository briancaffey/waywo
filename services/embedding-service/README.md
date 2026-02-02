# Embedding Service

A FastAPI microservice for creating document embeddings using the `nvidia/llama-embed-nemotron-8b` model.

See [https://huggingface.co/nvidia/llama-embed-nemotron-8b#usage](https://huggingface.co/nvidia/llama-embed-nemotron-8b#usage) for info about this service.
## Installation

```bash
cd services/embedding-service
uv sync
```

For flash attention support (faster inference on compatible GPUs):

```bash
uv sync --extra flash
```

## Running the Service

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

For development with auto-reload:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Usage

### Create Document Embeddings

```bash
curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -d '{"documents": ["First document text", "Second document text"]}'
```

Response:

```json
{
  "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]]
}
```

### Health Check

```bash
curl http://localhost:8000/health
```
