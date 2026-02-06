"""
LlamaIndex RAG workflow for the Waywo chatbot.

This workflow provides conversational access to project data using
vector similarity search and LLM-powered response generation.

Workflow Steps:
1. start -> ChatQueryEvent
2. generate_query_embedding -> QueryEmbeddingEvent
3. retrieve_projects -> ProjectsRetrievedEvent
4. generate_response -> StopEvent(ChatbotResult)
"""

import logging
from dataclasses import dataclass
from typing import Any

from llama_index.core import Settings
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores.types import (
    BasePydanticVectorStore,
    VectorStoreQuery,
    VectorStoreQueryResult,
)
from llama_index.core.workflow import (
    Context,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

from src.db_client import semantic_search
from src.embedding_client import get_single_embedding
from src.llm_config import get_llm
from src.models import WaywoProject
from src.workflows.events import (
    ChatQueryEvent,
    ChatResponseEvent,
    ProjectsRetrievedEvent,
    QueryEmbeddingEvent,
)
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


class WaywoChatbotWorkflow(Workflow):
    """
    RAG workflow for conversational access to Waywo projects.

    Uses LlamaIndex Workflow with @step decorators to process
    chat queries through semantic search and LLM response generation.

    Workflow Flow:
        StartEvent -> ChatQueryEvent -> QueryEmbeddingEvent ->
        ProjectsRetrievedEvent -> StopEvent(ChatbotResult)
    """

    def __init__(
        self,
        *args,
        embedding_url: str = "http://192.168.5.96:8000",
        top_k: int = 5,
        **kwargs,
    ):
        """
        Initialize the chatbot workflow.

        Args:
            embedding_url: URL of the embedding service
            top_k: Number of similar projects to retrieve for context
        """
        super().__init__(*args, **kwargs)
        self.embedding_url = embedding_url
        self.top_k = top_k
        self.llm = get_llm()

        # Configure LlamaIndex settings
        Settings.llm = self.llm
        Settings.embed_model = None  # We use our own embedding service

        # Create the vector store
        self.vector_store = WaywoVectorStore(embedding_url=embedding_url)

    @step
    async def start(self, ctx: Context, ev: StartEvent) -> ChatQueryEvent:
        """
        Initialize the chatbot workflow with query data.

        Extracts query and top_k from StartEvent and emits ChatQueryEvent.
        """
        query = ev.query
        top_k = ev.get("top_k", self.top_k)

        logger.info(f"🤖 Starting chatbot workflow for query: {query[:50]}...")

        # Store query in context for logging
        await ctx.store.set("query", query)

        return ChatQueryEvent(query=query, top_k=top_k)

    @step
    async def generate_query_embedding(
        self, ctx: Context, ev: ChatQueryEvent
    ) -> QueryEmbeddingEvent:
        """
        Generate embedding for the user's query.
        """
        logger.info(f"🧠 Generating query embedding...")

        try:
            query_embedding = await get_single_embedding(
                text=ev.query,
                embedding_url=self.embedding_url,
            )
            logger.info(f"✅ Got query embedding ({len(query_embedding)} dims)")

            return QueryEmbeddingEvent(
                query=ev.query,
                top_k=ev.top_k,
                query_embedding=query_embedding,
            )

        except Exception as e:
            logger.error(f"❌ Failed to get query embedding: {e}")
            # Return empty embedding - will result in no results
            return QueryEmbeddingEvent(
                query=ev.query,
                top_k=ev.top_k,
                query_embedding=[],
            )

    @step
    async def retrieve_projects(
        self, ctx: Context, ev: QueryEmbeddingEvent
    ) -> ProjectsRetrievedEvent:
        """
        Retrieve relevant projects using semantic search.
        """
        logger.info(f"📚 Retrieving projects with top_k={ev.top_k}...")

        projects: list[dict] = []
        context = "No relevant projects found in the database."

        if ev.query_embedding:
            try:
                results = semantic_search(
                    query_embedding=ev.query_embedding,
                    limit=ev.top_k,
                    is_valid=True,
                )
                logger.info(f"📚 Retrieved {len(results)} relevant projects")

                # Build context and project list
                if results:
                    context_parts = ["Here are the most relevant projects:\n"]

                    for i, (project, similarity) in enumerate(results, 1):
                        hashtags_str = ", ".join(f"#{tag}" for tag in project.hashtags)
                        context_parts.append(f"""
---
Project {i}: {project.title}
Relevance: {similarity:.0%}
Description: {project.description}
Tags: {hashtags_str}
Idea Score: {project.idea_score}/10 | Complexity Score: {project.complexity_score}/10
---""")

                        projects.append(
                            {
                                "id": project.id,
                                "title": project.title,
                                "short_description": project.short_description,
                                "similarity": round(similarity, 4),
                                "hashtags": project.hashtags,
                                "idea_score": project.idea_score,
                                "complexity_score": project.complexity_score,
                            }
                        )

                    context = "\n".join(context_parts)

            except Exception as e:
                logger.error(f"❌ Failed to retrieve projects: {e}")

        return ProjectsRetrievedEvent(
            query=ev.query,
            projects=projects,
            context=context,
        )

    @step
    async def generate_response(
        self, ctx: Context, ev: ProjectsRetrievedEvent
    ) -> StopEvent:
        """
        Generate a response using the LLM with context from retrieved projects.
        """
        logger.info(f"💬 Generating response...")

        try:
            prompt = chatbot_response_prompt(query=ev.query, context=ev.context)
            response = await self.llm.acomplete(prompt)
            response_text = str(response)
            logger.info("✅ Generated response")

        except Exception as e:
            logger.error(f"❌ Failed to generate response: {e}")
            response_text = "I'm sorry, I couldn't generate a response due to an error."

        result = ChatbotResult(
            response=response_text,
            source_projects=ev.projects,
            query=ev.query,
            projects_found=len(ev.projects),
        )

        return StopEvent(result=result)

    async def chat(self, query: str, top_k: int = None) -> ChatbotResult:
        """
        Convenience method to run a chat query.

        Args:
            query: The user's question or message
            top_k: Override the default top_k value

        Returns:
            ChatbotResult with response and source projects
        """
        if top_k is None:
            top_k = self.top_k

        result = await self.run(query=query, top_k=top_k)
        return result


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
        timeout=120,
    )
    return await chatbot.chat(query)
