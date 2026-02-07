from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.settings import EMBEDDING_URL, RERANK_URL
from src.clients.embedding import (
    EmbeddingError,
    check_embedding_service_health,
    get_single_embedding,
)
from src.clients.rerank import (
    RerankError,
    check_rerank_service_health,
    rerank_documents,
)
from src.db.client import (
    get_projects_with_embeddings_count,
    get_total_project_count,
    semantic_search,
)

router = APIRouter()


class SemanticSearchRequest(BaseModel):
    """Request body for semantic search."""

    query: str = Field(..., min_length=1, description="Search query text")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results to return")
    use_rerank: bool = Field(
        default=True, description="Use reranking to improve results"
    )


class ChatbotRequest(BaseModel):
    """Request body for chatbot query."""

    query: str = Field(..., min_length=1, description="User's question or message")
    top_k: int = Field(
        default=5, ge=1, le=20, description="Number of projects for context"
    )


@router.get("/api/embedding/health", tags=["semantic"])
async def embedding_service_health():
    """
    Check if the embedding service is healthy.
    """
    is_healthy = await check_embedding_service_health(EMBEDDING_URL)

    if not is_healthy:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": "Embedding service is not reachable",
                "url": EMBEDDING_URL,
            },
        )

    return JSONResponse(
        content={
            "status": "healthy",
            "url": EMBEDDING_URL,
        }
    )


@router.get("/api/rerank/health", tags=["semantic"])
async def rerank_service_health():
    """
    Check if the rerank service is healthy.
    """
    is_healthy = await check_rerank_service_health(RERANK_URL)

    if not is_healthy:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": "Rerank service is not reachable",
                "url": RERANK_URL,
            },
        )

    return JSONResponse(
        content={
            "status": "healthy",
            "url": RERANK_URL,
        }
    )


@router.get("/api/semantic-search/stats", tags=["semantic"])
async def semantic_search_stats():
    """
    Get statistics about semantic search capabilities.
    """
    total_projects = get_total_project_count()
    projects_with_embeddings = get_projects_with_embeddings_count()

    return {
        "total_projects": total_projects,
        "projects_with_embeddings": projects_with_embeddings,
        "embedding_coverage": (
            round(projects_with_embeddings / total_projects * 100, 1)
            if total_projects > 0
            else 0
        ),
    }


@router.post("/api/semantic-search", tags=["semantic"])
async def perform_semantic_search(request: SemanticSearchRequest):
    """
    Perform semantic search over projects using vector similarity.

    When use_rerank is True (default), fetches more candidates and reranks
    them using the rerank service for improved relevance.

    Returns the most similar/relevant projects based on the query.
    """
    try:
        # Get embedding for the query
        query_embedding = await get_single_embedding(
            text=request.query,
            embedding_url=EMBEDDING_URL,
        )
    except EmbeddingError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Embedding service error: {str(e)}",
        )

    # Fetch more candidates if reranking is enabled
    candidate_limit = request.limit * 3 if request.use_rerank else request.limit

    # Perform semantic search
    results = semantic_search(
        query_embedding=query_embedding,
        limit=candidate_limit,
        is_valid=True,
    )

    # Build original results (top N by similarity)
    original_results = [
        {
            "project": project.model_dump(),
            "similarity": round(similarity, 4),
        }
        for project, similarity in results[: request.limit]
    ]

    # Rerank results if enabled
    reranked = False
    formatted_results = original_results

    if request.use_rerank and results:
        try:
            # Prepare documents for reranking (title + description)
            documents = [
                f"{project.title}: {project.description}" for project, _ in results
            ]

            rerank_result = await rerank_documents(
                query=request.query,
                documents=documents,
                rerank_url=RERANK_URL,
            )

            # Reorder results based on rerank scores
            reranked_results = []
            for idx in rerank_result.ranked_indices[: request.limit]:
                project, similarity = results[idx]
                reranked_results.append(
                    {
                        "project": project.model_dump(),
                        "similarity": round(similarity, 4),
                        "rerank_score": round(rerank_result.scores[idx], 4),
                    }
                )

            reranked = True
            formatted_results = reranked_results

        except RerankError:
            # Fall back to similarity-based ordering (already set above)
            pass

    response = {
        "results": formatted_results,
        "query": request.query,
        "total": len(formatted_results),
        "reranked": reranked,
    }

    # Include original results for comparison when reranking was used
    if reranked:
        response["original_results"] = original_results

    return response


@router.post("/api/waywo-chatbot", tags=["semantic"])
async def chatbot_query(request: ChatbotRequest):
    """
    Query the RAG chatbot about projects.

    Uses semantic search with reranking to find relevant projects and generates
    a conversational response using an LLM.
    """
    from src.workflows.waywo_chatbot_workflow import run_chatbot_query

    try:
        result = await run_chatbot_query(
            query=request.query,
            embedding_url=EMBEDDING_URL,
            rerank_url=RERANK_URL,
            top_k=request.top_k,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chatbot error: {str(e)}",
        )

    return {
        "response": result.response,
        "source_projects": result.source_projects,
        "query": result.query,
        "projects_found": result.projects_found,
    }
