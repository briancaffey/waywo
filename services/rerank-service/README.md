# Rerank Service

A FastAPI microservice for reranking documents using the `nvidia/llama-nemotron-rerank-1b-v2` model.

See [https://huggingface.co/nvidia/llama-nemotron-rerank-1b-v2](https://huggingface.co/nvidia/llama-nemotron-rerank-1b-v2) for info about this model.

## Installation

```bash
cd services/rerank-service
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

## API Usage

### Rerank Documents

```bash
curl -X POST http://localhost:8001/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "query": "how much protein should a female eat?",
    "documents": [
      "As a general guideline, the CDC average requirement of protein for women is 46 grams per day.",
      "Definition of summit for English Language Learners: the highest point of a mountain.",
      "Calorie intake should not fall below 1,200 a day for women."
    ]
  }'
```

Response:

```json
{
  "scores": [0.85, -0.12, 0.45],
  "ranked_indices": [0, 2, 1]
}
```

- `scores`: Raw logit scores for each document (higher = more relevant)
- `ranked_indices`: Document indices sorted by relevance (most relevant first)

### Health Check

```bash
curl http://localhost:8001/health
```

Response:

```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda:0"
}
```

## Model Details

- **Model**: nvidia/llama-nemotron-rerank-1b-v2
- **Type**: Cross-encoder reranker
- **Max sequence length**: 512 tokens (configurable up to 8192)
- **Languages**: 26 languages supported
