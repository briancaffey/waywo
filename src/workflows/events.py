"""
LlamaIndex workflow events for waywo project processing.

Events are Pydantic models that carry data between workflow steps.
"""

from typing import Optional

from llama_index.core.workflow import Event


class CommentInputEvent(Event):
    """
    Initial event containing the raw comment data to process.

    This is emitted at the start of the workflow after receiving the StartEvent.
    """

    comment_id: int
    comment_text: str
    comment_author: Optional[str] = None
    comment_time: Optional[int] = None
    parent_post_id: Optional[int] = None


class ExtractedProjectEvent(Event):
    """
    Event emitted after extracting project(s) from a comment.

    If a comment contains multiple projects, multiple events are emitted.
    """

    comment_id: int
    project_index: int  # 0-indexed, for multi-project comments
    total_projects: int  # Total number of projects in this comment
    raw_text: str  # The portion of text describing this specific project
    original_comment_text: str  # Full original comment for reference


class ValidatedProjectEvent(Event):
    """
    Event emitted after validating whether extracted text is a real project.
    """

    comment_id: int
    project_index: int
    total_projects: int
    raw_text: str
    original_comment_text: str

    # Validation results
    is_valid: bool
    invalid_reason: Optional[str] = (
        None  # e.g., "deleted", "not a project", "personal task"
    )


class URLsFetchedEvent(Event):
    """
    Event emitted after extracting and fetching URLs from project text.
    """

    comment_id: int
    project_index: int
    total_projects: int
    raw_text: str
    original_comment_text: str
    is_valid: bool
    invalid_reason: Optional[str] = None

    # URL data
    urls: list[str]  # Extracted URLs
    url_contents: dict[
        str, str
    ]  # URL -> markdown content (empty string if fetch failed)
    url_errors: dict[str, str]  # URL -> error message for failed fetches


class MetadataGeneratedEvent(Event):
    """
    Event emitted after generating metadata (title, description, tags, etc.)
    """

    comment_id: int
    project_index: int
    total_projects: int
    raw_text: str
    original_comment_text: str
    is_valid: bool
    invalid_reason: Optional[str] = None
    urls: list[str]
    url_contents: dict[str, str]
    url_errors: dict[str, str]

    # Generated metadata
    title: str
    short_description: str  # 5-10 words
    description: str  # 1-2 sentences
    hashtags: list[str]  # 3-5 tags
    url_summaries: dict[str, str]  # URL -> summary of content


class ScoredProjectEvent(Event):
    """
    Event emitted after scoring the project.
    """

    comment_id: int
    project_index: int
    total_projects: int
    raw_text: str
    original_comment_text: str
    is_valid: bool
    invalid_reason: Optional[str] = None
    urls: list[str]
    url_contents: dict[str, str]
    url_errors: dict[str, str]
    title: str
    short_description: str
    description: str
    hashtags: list[str]
    url_summaries: dict[str, str]

    # Scores
    idea_score: int  # 1-10
    complexity_score: int  # 1-10


class EmbeddingGeneratedEvent(Event):
    """
    Event emitted after generating the embedding for semantic search.
    """

    comment_id: int
    project_index: int
    total_projects: int
    raw_text: str
    original_comment_text: str
    is_valid: bool
    invalid_reason: Optional[str] = None
    urls: list[str]
    url_contents: dict[str, str]
    url_errors: dict[str, str]
    title: str
    short_description: str
    description: str
    hashtags: list[str]
    url_summaries: dict[str, str]
    idea_score: int
    complexity_score: int

    # Embedding
    embedding: Optional[list[float]] = None  # Vector embedding for semantic search


class ProjectCompleteEvent(Event):
    """
    Final event representing a fully processed project ready to save.

    This is collected by the workflow to build the final output.
    """

    comment_id: int
    project_index: int
    total_projects: int

    # Core data
    is_valid: bool
    invalid_reason: Optional[str] = None
    title: str
    short_description: str
    description: str
    hashtags: list[str]
    urls: list[str]
    url_summaries: dict[str, str]
    idea_score: int
    complexity_score: int

    # Embedding
    embedding: Optional[list[float]] = None

    # Logs for debugging
    workflow_logs: list[str]


# =============================================================================
# Chatbot Workflow Events
# =============================================================================


class ChatQueryEvent(Event):
    """
    Event containing the user's chat query to process.

    Emitted after StartEvent to begin the chatbot workflow.
    """

    query: str
    top_k: int = 5


class QueryEmbeddingEvent(Event):
    """
    Event emitted after generating the embedding for the user's query.
    """

    query: str
    top_k: int
    query_embedding: list[float]


class ProjectsCandidatesEvent(Event):
    """
    Event emitted after retrieving candidate projects via semantic search.

    This is an intermediate step before reranking.
    """

    query: str
    top_k: int
    candidates: list[dict]  # List of candidate projects with similarity scores


class ProjectsRetrievedEvent(Event):
    """
    Event emitted after retrieving relevant projects via semantic search.
    """

    query: str
    projects: list[dict]
    context: str


class ChatResponseEvent(Event):
    """
    Final event containing the chatbot's response.
    """

    query: str
    response: str
    source_projects: list[dict]
    projects_found: int
