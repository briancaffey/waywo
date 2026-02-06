"""
Workflow configuration and metadata for visualization.

Provides workflow instances and metadata for the visualization API.
"""

import os

from src.workflows import (
    # Project workflow and events
    WaywoProjectWorkflow,
    CommentInputEvent,
    ExtractedProjectEvent,
    ValidatedProjectEvent,
    URLsFetchedEvent,
    MetadataGeneratedEvent,
    ScoredProjectEvent,
    EmbeddingGeneratedEvent,
    ProjectCompleteEvent,
    # Chatbot workflow and events
    WaywoChatbotWorkflow,
    ChatQueryEvent,
    QueryEmbeddingEvent,
    ProjectsRetrievedEvent,
    ChatResponseEvent,
)

# Environment configuration
FIRECRAWL_URL = os.environ.get("FIRECRAWL_URL", "http://localhost:3002")
EMBEDDING_URL = os.environ.get("EMBEDDING_URL", "http://192.168.5.96:8000")


def create_project_workflow() -> WaywoProjectWorkflow:
    """Create an instance of the project processing workflow."""
    return WaywoProjectWorkflow(
        timeout=300,
        firecrawl_url=FIRECRAWL_URL,
        embedding_url=EMBEDDING_URL,
    )


def create_chatbot_workflow() -> WaywoChatbotWorkflow:
    """Create an instance of the chatbot workflow."""
    return WaywoChatbotWorkflow(
        timeout=120,
        embedding_url=EMBEDDING_URL,
        top_k=5,
    )


# Create workflow instances for visualization
project_workflow = create_project_workflow()
chatbot_workflow = create_chatbot_workflow()

# Map of workflow names to instances
WORKFLOWS = {
    "project": project_workflow,
    "chatbot": chatbot_workflow,
}

# Metadata about available workflows for the API
WORKFLOW_METADATA = {
    "project": {
        "name": "project",
        "description": "Process HN comments into projects",
        "steps": 8,
        "events": [
            "CommentInputEvent",
            "ExtractedProjectEvent",
            "ValidatedProjectEvent",
            "URLsFetchedEvent",
            "MetadataGeneratedEvent",
            "ScoredProjectEvent",
            "EmbeddingGeneratedEvent",
            "ProjectCompleteEvent",
        ],
    },
    "chatbot": {
        "name": "chatbot",
        "description": "RAG chatbot for project Q&A",
        "steps": 4,
        "events": [
            "ChatQueryEvent",
            "QueryEmbeddingEvent",
            "ProjectsRetrievedEvent",
            "ChatResponseEvent",
        ],
    },
}
