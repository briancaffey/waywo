"""
LlamaIndex workflows for processing waywo comments into projects.
"""

from src.workflows.waywo_chatbot_workflow import (
    ChatbotResult,
    WaywoChatbotWorkflow,
    WaywoVectorStore,
    run_chatbot_query,
)
from src.workflows.waywo_project_workflow import WaywoProjectWorkflow
from src.workflows.events import (
    # Project workflow events
    CommentInputEvent,
    EmbeddingGeneratedEvent,
    ExtractedProjectEvent,
    MetadataGeneratedEvent,
    ProjectCompleteEvent,
    ScoredProjectEvent,
    URLsFetchedEvent,
    ValidatedProjectEvent,
    # Chatbot workflow events
    ChatQueryEvent,
    ChatResponseEvent,
    ProjectsRetrievedEvent,
    QueryEmbeddingEvent,
)

__all__ = [
    # Workflows
    "WaywoProjectWorkflow",
    "WaywoChatbotWorkflow",
    # Chatbot helpers
    "ChatbotResult",
    "WaywoVectorStore",
    "run_chatbot_query",
    # Project workflow events
    "CommentInputEvent",
    "EmbeddingGeneratedEvent",
    "ExtractedProjectEvent",
    "MetadataGeneratedEvent",
    "ProjectCompleteEvent",
    "ScoredProjectEvent",
    "URLsFetchedEvent",
    "ValidatedProjectEvent",
    # Chatbot workflow events
    "ChatQueryEvent",
    "ChatResponseEvent",
    "ProjectsRetrievedEvent",
    "QueryEmbeddingEvent",
]
