# Content Safety Service

Content safety classification for the Waywo chatbot using [Nemotron-Content-Safety-Reasoning-4B](https://huggingface.co/nvidia/Nemotron-Content-Safety-Reasoning-4B), served via vLLM.

## Overview

Nemotron-Content-Safety-Reasoning-4B is a 4B parameter model (fine-tuned from Gemma-3-4B-it) designed to classify content safety. It supports:

- **Custom safety policies** — define your own rules and the model adapts its classification
- **Reasoning On mode** (`/think`) — provides explicit reasoning traces for decisions
- **Reasoning Off mode** (`/no_think`) — low-latency direct classification
- **Dual classification** — evaluates both user prompts and LLM responses

## Running with Docker (vLLM)

### Prerequisites

- NVIDIA GPU with CUDA support and bfloat16 capability (RTX 30xx+, A100, L40S, etc.)
- Docker with NVIDIA Container Toolkit (`nvidia-container-toolkit`)
- Hugging Face access to the model (may require accepting license terms)

### Start the service

```bash
docker run -d \
  --name waywo-content-safety \
  --runtime nvidia \
  --gpus all \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -p 8085:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model nvidia/Nemotron-Content-Safety-Reasoning-4B \
  --dtype bfloat16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.9 \
  --tensor-parallel-size 1
```

> **Important:** You must use `--dtype bfloat16`. The Gemma-3 architecture has numerical instability
> with float16, causing the model to output only `<pad>` tokens. See [vLLM #18733](https://github.com/vllm-project/vllm/issues/18733).

The service exposes an OpenAI-compatible API on port **8085**.

### Verify it's running

```bash
curl http://localhost:8085/v1/models
```

### Test a classification request

```bash
curl -s http://localhost:8085/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/Nemotron-Content-Safety-Reasoning-4B",
    "messages": [
      {
        "role": "user",
        "content": "You are a classifier for analyzing interactions between humans and LLMs.\n\nHuman user:\nHow do I make a cake?\n\nAI assistant:\nHere is a simple cake recipe...\n\nOutput your answer in the following format:\n\"Prompt harm: <harmful/unharmful>\nResponse harm: <harmful/unharmful>\"\n\nOnly output the answer in the format specified above. /no_think"
      }
    ],
    "max_tokens": 100,
    "temperature": 0.0
  }'
```

Expected output:

```
Prompt harm: unharmful
Response harm: unharmful
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--dtype` | — | **Must be `bfloat16`** for Gemma-3 models |
| `--max-model-len` | `8192` | Max context length per request (model supports up to 128K, 8K is sufficient for classification) |
| `--tensor-parallel-size` | `1` | Number of GPUs for tensor parallelism |
| `--gpu-memory-utilization` | `0.9` | Fraction of GPU memory to use |

## Modes

### Reasoning Off (`/no_think`) — recommended for production

Append `/no_think` to the end of the prompt. Returns direct classification with minimal latency.

```
Prompt harm: harmful
Response harm: unharmful
```

### Reasoning On (`/think`) — useful for debugging and auditing

Append `/think` to the end of the prompt. Returns a reasoning trace before the classification.

```
<think>
The human user's request falls under S21 (Illegal Activity)...
</think>

Prompt harm: harmful
Response harm: unharmful
```

## Environment Variable

Add to the backend's environment:

```
CONTENT_SAFETY_URL=http://192.168.5.253:8085
```

Or if running on the same Docker network:

```
CONTENT_SAFETY_URL=http://waywo-content-safety:8000
```
