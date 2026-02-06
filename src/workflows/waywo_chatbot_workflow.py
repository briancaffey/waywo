"""
LlamaIndex RAG workflow for the Waywo chatbot.

This workflow provides conversational access to project data using
vector similarity search and LLM-powered response generation.
"""

import logging
from dataclasses import dataclass
from typing import Any

from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.vector_stores.types import (
    BasePydanticVectorStore,
    VectorStoreQuery,
    VectorStoreQueryResult,
)

from src.db_client import get_all_projects, semantic_search
from src.embedding_client import get_single_embedding
from src.llm_config import get_llm
from src.models import WaywoProject
from src.workflows.prompts import CHATBOT_SYSTEM_PROMPT as WAYWO_SYSTEM_PROMPT
from src.workflows.prompts import chatbot_response_prompt

logger = logging.getLogger(__name__)


@dataclass
class ChatbotResult:
    """Result from the chatbot workflow."""

    response: str
    source_projects: list[dict[str, Any]]
    query: str
    projects_found: int


class WaywoVectorStore(BasePydanticVectorStore):
    """
    Custom LlamaIndex vector store that uses SQLite with sqlite-vector.

    This adapter allows LlamaIndex to query our existing waywo_projects table
    using the description_embedding column for similarity search.
    """

    stores_text: bool = True
    is_embedding_query: bool = True
    embedding_url: str = "http://192.168.5.96:8000"

    def __init__(self, embedding_url: str = "http://192.168.5.96:8000", **kwargs):
        super().__init__(embedding_url=embedding_url, **kwargs)

    @classmethod
    def class_name(cls) -> str:
        return "WaywoVectorStore"

    @property
    def client(self) -> Any:
        """Return the underlying client (not used for this implementation)."""
        return None

    def add(self, nodes: list[TextNode], **kwargs) -> list[str]:
        """Add nodes to vector store (not implemented - we use existing data)."""
        raise NotImplementedError("WaywoVectorStore is read-only")

    def delete(self, ref_doc_id: str, **kwargs) -> None:
        """Delete nodes from vector store (not implemented)."""
        raise NotImplementedError("WaywoVectorStore is read-only")

    def query(self, query: VectorStoreQuery, **kwargs) -> VectorStoreQueryResult:
        """
        Query the vector store using semantic search.

        Args:
            query: VectorStoreQuery with query_embedding and similarity_top_k

        Returns:
            VectorStoreQueryResult with matching nodes and similarities
        """
        import asyncio

        if query.query_embedding is None:
            return VectorStoreQueryResult(nodes=[], similarities=[], ids=[])

        # Perform semantic search using our db_client
        results = semantic_search(
            query_embedding=query.query_embedding,
            limit=query.similarity_top_k or 10,
            is_valid=True,  # Only return valid projects
        )

        nodes = []
        similarities = []
        ids = []

        for project, similarity in results:
            # Create a TextNode from the project
            node = TextNode(
                text=self._project_to_text(project),
                id_=str(project.id),
                metadata={
                    "project_id": project.id,
                    "title": project.title,
                    "short_description": project.short_description,
                    "hashtags": project.hashtags,
                    "idea_score": project.idea_score,
                    "complexity_score": project.complexity_score,
                    "source_comment_id": project.source_comment_id,
                },
            )
            nodes.append(node)
            similarities.append(similarity)
            ids.append(str(project.id))

        return VectorStoreQueryResult(
            nodes=nodes,
            similarities=similarities,
            ids=ids,
        )

    def _project_to_text(self, project: WaywoProject) -> str:
        """Convert a project to text for context."""
        hashtags_str = ", ".join(f"#{tag}" for tag in project.hashtags)
        return f"""Project: {project.title}
Description: {project.description}
Short Description: {project.short_description}
Tags: {hashtags_str}
Idea Score: {project.idea_score}/10
Complexity Score: {project.complexity_score}/10"""


class WaywoChatbotWorkflow:
    """
    RAG workflow for conversational access to Waywo projects.

    Uses LlamaIndex VectorStoreIndex with a custom vector store that
    queries our SQLite database with sqlite-vector.
    """

    def __init__(
        self,
        embedding_url: str = "http://192.168.5.96:8000",
        top_k: int = 5,
    ):
        """
        Initialize the chatbot workflow.

        Args:
            embedding_url: URL of the embedding service
            top_k: Number of similar projects to retrieve for context
        """
        self.embedding_url = embedding_url
        self.top_k = top_k
        self.llm = get_llm()

        # Configure LlamaIndex settings
        Settings.llm = self.llm
        Settings.embed_model = None  # We use our own embedding service

        # Create the vector store and index
        self.vector_store = WaywoVectorStore(embedding_url=embedding_url)

    async def _get_query_embedding(self, query: str) -> list[float]:
        """Get embedding for the user's query."""
        return await get_single_embedding(
            text=query,
            embedding_url=self.embedding_url,
        )

    async def _retrieve_projects(
        self, query_embedding: list[float]
    ) -> list[tuple[WaywoProject, float]]:
        """Retrieve relevant projects using semantic search."""
        return semantic_search(
            query_embedding=query_embedding,
            limit=self.top_k,
            is_valid=True,
        )

    def _build_context(
        self, projects: list[tuple[WaywoProject, float]]
    ) -> str:
        """Build context string from retrieved projects."""
        if not projects:
            return "No relevant projects found in the database."

        context_parts = ["Here are the most relevant projects:\n"]

        for i, (project, similarity) in enumerate(projects, 1):
            hashtags_str = ", ".join(f"#{tag}" for tag in project.hashtags)
            context_parts.append(f"""
---
Project {i}: {project.title}
Relevance: {similarity:.0%}
Description: {project.description}
Tags: {hashtags_str}
Idea Score: {project.idea_score}/10 | Complexity Score: {project.complexity_score}/10
---""")

        return "\n".join(context_parts)

    async def _generate_response(self, query: str, context: str) -> str:
        """Generate a response using the LLM with context."""
        prompt = chatbot_response_prompt(query=query, context=context)
        response = await self.llm.acomplete(prompt)
        return str(response)

    async def chat(self, query: str) -> ChatbotResult:
        """
        Process a chat message and return a response.

        Args:
            query: The user's question or message

        Returns:
            ChatbotResult with response and source projects
        """
        logger.info(f"🤖 Processing chat query: {query[:50]}...")

        # Step 1: Get query embedding
        try:
            query_embedding = await self._get_query_embedding(query)
            logger.info(f"✅ Got query embedding ({len(query_embedding)} dims)")
        except Exception as e:
            logger.error(f"❌ Failed to get query embedding: {e}")
            return ChatbotResult(
                response="I'm sorry, I couldn't process your question due to an embedding service error.",
                source_projects=[],
                query=query,
                projects_found=0,
            )

        # Step 2: Retrieve relevant projects
        try:
            results = await self._retrieve_projects(query_embedding)
            logger.info(f"📚 Retrieved {len(results)} relevant projects")
        except Exception as e:
            logger.error(f"❌ Failed to retrieve projects: {e}")
            results = []

        # Step 3: Build context
        context = self._build_context(results)

        # Step 4: Generate response
        try:
            response = await self._generate_response(query, context)
            logger.info("✅ Generated response")
        except Exception as e:
            logger.error(f"❌ Failed to generate response: {e}")
            response = "I'm sorry, I couldn't generate a response due to an error."

        # Build source projects list for the response
        source_projects = [
            {
                "id": project.id,
                "title": project.title,
                "short_description": project.short_description,
                "similarity": round(similarity, 4),
                "hashtags": project.hashtags,
                "idea_score": project.idea_score,
                "complexity_score": project.complexity_score,
            }
            for project, similarity in results
        ]

        return ChatbotResult(
            response=response,
            source_projects=source_projects,
            query=query,
            projects_found=len(results),
        )


async def run_chatbot_query(
    query: str,
    embedding_url: str = "http://192.168.5.96:8000",
    top_k: int = 5,
) -> ChatbotResult:
    """
    Convenience function to run a single chatbot query.

    Args:
        query: The user's question
        embedding_url: URL of the embedding service
        top_k: Number of similar projects to retrieve

    Returns:
        ChatbotResult with response and source projects
    """
    chatbot = WaywoChatbotWorkflow(
        embedding_url=embedding_url,
        top_k=top_k,
    )
    return await chatbot.chat(query)
