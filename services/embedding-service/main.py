from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

model: SentenceTransformer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    attn_implementation = "eager"
    model = SentenceTransformer(
        "nvidia/llama-embed-nemotron-8b",
        trust_remote_code=True,
        model_kwargs={
            "attn_implementation": attn_implementation,
            "torch_dtype": "bfloat16",
        },
        tokenizer_kwargs={"padding_side": "left"},
    )
    yield
    model = None


app = FastAPI(
    title="Embedding Service",
    description="Microservice for creating document embeddings",
    lifespan=lifespan,
)


class EmbedRequest(BaseModel):
    documents: list[str]


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]


@app.post("/embed", response_model=EmbedResponse)
async def embed_documents(request: EmbedRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if not request.documents:
        raise HTTPException(status_code=400, detail="No documents provided")

    embeddings = model.encode_document(request.documents)
    return EmbedResponse(embeddings=embeddings.tolist())


@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": model is not None}
