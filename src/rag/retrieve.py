"""Shared relevance-gated RAG retrieval used by both text and voice chat."""

import logging
from dataclasses import dataclass, field

from src.clients.embedding import get_single_embedding
from src.clients.rerank import RerankError, rerank_documents
from src.db.search import semantic_search
from src.settings import EMBEDDING_URL, RAG_SIMILARITY_THRESHOLD, RERANK_URL

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    context_text: str = ""
    source_projects: list[dict] = field(default_factory=list)
    projects_found: int = 0
    was_triggered: bool = False
    top_similarity: float = 0.0


async def smart_retrieve(
    query: str,
    similarity_threshold: float | None = None,
    top_k: int = 5,
    candidate_multiplier: int = 3,
) -> RAGContext:
    """Embed, search, and conditionally rerank to produce RAG context.

    Steps:
      1. Embed the query
      2. Semantic search for candidates
      3. If top similarity >= threshold → rerank and build context
      4. Otherwise return empty context (was_triggered=False)
    """
    if similarity_threshold is None:
        similarity_threshold = RAG_SIMILARITY_THRESHOLD

    # Step 1: embed
    try:
        query_embedding = await get_single_embedding(query, embedding_url=EMBEDDING_URL)
    except Exception as e:
        logger.error(f"RAG embed failed: {e}")
        return RAGContext()

    if not query_embedding:
        return RAGContext()

    # Step 2: semantic search
    candidate_limit = top_k * candidate_multiplier
    try:
        results = semantic_search(
            query_embedding=query_embedding,
            limit=candidate_limit,
            is_valid=True,
        )
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return RAGContext()

    if not results:
        return RAGContext()

    top_similarity = results[0][1]
    logger.info(f"RAG top similarity: {top_similarity:.4f} (threshold: {similarity_threshold})")

    if top_similarity < similarity_threshold:
        return RAGContext(top_similarity=top_similarity)

    # Step 3: rerank & build context
    candidates = []
    for project, similarity in results:
        candidates.append({
            "id": project.id,
            "title": project.title,
            "short_description": project.short_description,
            "description": project.description,
            "similarity": round(similarity, 4),
            "hashtags": project.hashtags,
            "idea_score": project.idea_score,
            "complexity_score": project.complexity_score,
        })

    source_projects: list[dict] = []
    context_text = ""

    try:
        documents = [f"{c['title']}: {c['description']}" for c in candidates]
        rerank_result = await rerank_documents(
            query=query,
            documents=documents,
            rerank_url=RERANK_URL,
        )

        reranked = []
        for idx in rerank_result.ranked_indices[:top_k]:
            candidate = candidates[idx]
            candidate["rerank_score"] = rerank_result.scores[idx]
            reranked.append(candidate)

        context_text, source_projects = _build_context(reranked, use_rerank=True)

    except (RerankError, Exception) as e:
        logger.warning(f"RAG rerank failed, falling back to similarity order: {e}")
        fallback = candidates[:top_k]
        context_text, source_projects = _build_context(fallback, use_rerank=False)

    return RAGContext(
        context_text=context_text,
        source_projects=source_projects,
        projects_found=len(source_projects),
        was_triggered=True,
        top_similarity=top_similarity,
    )


def _build_context(
    projects: list[dict], use_rerank: bool
) -> tuple[str, list[dict]]:
    """Format project list into context text and source metadata."""
    if not projects:
        return "No relevant projects found in the database.", []

    parts = ["Here are the most relevant projects:\n"]
    sources = []

    for i, p in enumerate(projects, 1):
        hashtags_str = ", ".join(f"#{tag}" for tag in p["hashtags"])
        score_label = (
            f"Relevance Score: {p['rerank_score']:.2f}"
            if use_rerank and "rerank_score" in p
            else f"Relevance: {p['similarity']:.0%}"
        )
        parts.append(
            f"\n---\n"
            f"Project {i}: {p['title']}\n"
            f"{score_label}\n"
            f"Description: {p['description']}\n"
            f"Tags: {hashtags_str}\n"
            f"Idea Score: {p['idea_score']}/10 | Complexity Score: {p['complexity_score']}/10\n"
            f"---"
        )
        sources.append({
            "id": p["id"],
            "title": p["title"],
            "short_description": p["short_description"],
            "similarity": p["similarity"],
            "hashtags": p["hashtags"],
            "idea_score": p["idea_score"],
            "complexity_score": p["complexity_score"],
        })

    return "\n".join(parts), sources
