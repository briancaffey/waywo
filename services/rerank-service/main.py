from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer

model: AutoModelForSequenceClassification | None = None
tokenizer: AutoTokenizer | None = None
device: str = "cuda:0" if torch.cuda.is_available() else "cpu"
max_length: int = 512


def prompt_template(query: str, passage: str) -> str:
    return f"question:{query} \n \n passage:{passage}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, tokenizer

    model_name = "nvidia/llama-nemotron-rerank-1b-v2"

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
        padding_side="left",
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    ).eval()

    if model.config.pad_token_id is None:
        model.config.pad_token_id = tokenizer.eos_token_id

    model = model.to(device)

    yield

    model = None
    tokenizer = None


app = FastAPI(
    title="Rerank Service",
    description="Microservice for reranking documents using llama-nemotron-rerank",
    lifespan=lifespan,
)


class RerankRequest(BaseModel):
    query: str
    documents: list[str]


class RerankResponse(BaseModel):
    scores: list[float]
    ranked_indices: list[int]


@app.post("/rerank", response_model=RerankResponse)
async def rerank_documents(request: RerankRequest):
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if not request.query:
        raise HTTPException(status_code=400, detail="No query provided")
    if not request.documents:
        raise HTTPException(status_code=400, detail="No documents provided")

    texts = [prompt_template(request.query, doc) for doc in request.documents]

    batch_dict = tokenizer(
        texts,
        padding=True,
        truncation=True,
        return_tensors="pt",
        max_length=max_length,
    )

    batch_dict = {k: v.to(device) for k, v in batch_dict.items()}

    with torch.inference_mode():
        logits = model(**batch_dict).logits
        scores = logits.view(-1).cpu().tolist()

    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    return RerankResponse(scores=scores, ranked_indices=ranked_indices)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "device": device,
    }
