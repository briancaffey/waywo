from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HNItem(BaseModel):
    """Base model for Hacker News items with common fields."""

    id: int
    type: str
    by: Optional[str] = None
    time: Optional[int] = None
    text: Optional[str] = None
    dead: Optional[bool] = None
    deleted: Optional[bool] = None
    kids: Optional[list[int]] = None


class WaywoPost(HNItem):
    """A monthly 'What are you working on?' HN post (story type)."""

    title: Optional[str] = None
    url: Optional[str] = None
    score: Optional[int] = None
    descendants: Optional[int] = None

    # Metadata from waywo.yml
    year: Optional[int] = None
    month: Optional[int] = None


class WaywoComment(HNItem):
    """A top-level reply on a WaywoPost (someone's project submission)."""

    parent: Optional[int] = None


class WaywoYamlEntry(BaseModel):
    """Entry from waywo.yml file."""

    id: int
    year: int
    month: int


class ProcessWaywoPostsRequest(BaseModel):
    """Request body for POST /api/process-waywo-posts."""

    limit_posts: Optional[int] = None
    limit_comments: Optional[int] = None


class AddWaywoPostRequest(BaseModel):
    """Request body for POST /api/waywo-posts/add."""

    url: str


class WaywoPostSummary(BaseModel):
    """Summary of a WaywoPost for list views."""

    id: int
    title: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    score: Optional[int] = None
    comment_count: int = 0
    descendants: Optional[int] = None


class WaywoProject(BaseModel):
    """Extracted project data from a WaywoComment."""

    id: int
    source_comment_id: Optional[int] = None
    source: Optional[str] = None

    # Validation
    is_valid_project: bool = True
    invalid_reason: Optional[str] = None

    # Core metadata
    title: str
    short_description: str  # 5-10 words
    description: str  # 1-2 sentences
    hashtags: list[str] = Field(default_factory=list)  # 3-5 tags

    # URLs
    project_urls: list[str] = Field(default_factory=list)
    url_summaries: dict[str, str] = Field(default_factory=dict)
    primary_url: Optional[str] = None
    url_contents: dict[str, str] = Field(default_factory=dict)

    # Scores (1-10)
    idea_score: int = Field(ge=1, le=10)
    complexity_score: int = Field(ge=1, le=10)

    # Timestamps
    created_at: datetime
    processed_at: datetime
    comment_time: Optional[int] = None  # HN comment Unix timestamp

    # Workflow metadata
    workflow_logs: list[str] = Field(default_factory=list)

    # Bookmarking
    is_bookmarked: bool = False

    # Screenshot
    screenshot_path: Optional[str] = None


class WaywoProjectSubmission(BaseModel):
    """A record of a project being posted in a comment."""

    id: int
    project_id: int
    comment_id: int
    extracted_text: Optional[str] = None
    similarity_score: Optional[float] = None
    created_at: datetime

    # Enriched fields (populated from joins)
    comment_by: Optional[str] = None
    comment_time: Optional[int] = None
    post_id: Optional[int] = None
    post_title: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None


class WaywoProjectSummary(BaseModel):
    """Summary of a WaywoProject for list views."""

    id: int
    source_comment_id: Optional[int] = None
    source: Optional[str] = None
    title: str
    short_description: str
    hashtags: list[str]
    idea_score: int
    complexity_score: int
    is_valid_project: bool
    is_bookmarked: bool
    screenshot_path: Optional[str] = None
    primary_url: Optional[str] = None
    created_at: datetime


class ProcessCommentRequest(BaseModel):
    """Request body for processing a single comment."""

    pass  # No parameters needed, comment_id comes from URL


class ProcessCommentsRequest(BaseModel):
    """Request body for batch processing comments."""

    limit: Optional[int] = None  # Limit for testing


class WaywoProjectListFilters(BaseModel):
    """Query parameters for filtering WaywoProject list."""

    tags: Optional[list[str]] = None
    min_idea_score: Optional[int] = Field(None, ge=1, le=10)
    max_idea_score: Optional[int] = Field(None, ge=1, le=10)
    min_complexity_score: Optional[int] = Field(None, ge=1, le=10)
    max_complexity_score: Optional[int] = Field(None, ge=1, le=10)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    is_valid: Optional[bool] = None
    source: Optional[str] = None


# ---------------------------------------------------------------------------
# Video models
# ---------------------------------------------------------------------------


class WaywoVideoSegment(BaseModel):
    """A single segment within a generated video."""

    id: int
    video_id: int
    segment_index: int

    # Script data
    segment_type: str  # hook | introduction | features | audience | closing
    narration_text: str
    scene_description: str  # Original from LLM (preserved)
    image_prompt: str  # Editable, defaults to scene_description
    visual_style: str = "abstract"
    transition: str = "fade"

    # Audio
    audio_path: Optional[str] = None
    audio_duration_seconds: Optional[float] = None

    # Image
    image_path: Optional[str] = None
    image_name: Optional[str] = None  # InvokeAI image name

    # Transcription (word-level timestamps)
    transcription: Optional[dict] = None

    # Status
    status: str = "pending"
    error_message: Optional[str] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime


class WaywoVideo(BaseModel):
    """A generated video for a project."""

    id: int
    project_id: int
    version: int = 1

    # Script metadata
    video_title: Optional[str] = None
    video_style: Optional[str] = None
    script_json: Optional[dict] = None

    # Voice
    voice_name: Optional[str] = None

    # Status
    status: str = "pending"
    error_message: Optional[str] = None

    # Output
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None

    # Video metadata
    duration_seconds: Optional[float] = None
    width: int = 1080
    height: int = 1920

    # Workflow
    workflow_logs: list[str] = Field(default_factory=list)

    # User interaction
    view_count: int = 0
    is_favorited: bool = False

    # Timestamps
    created_at: datetime
    completed_at: Optional[datetime] = None

    # Segments (populated when fetching with detail)
    segments: list[WaywoVideoSegment] = Field(default_factory=list)


class GenerateIdeasRequest(BaseModel):
    """Request body for POST /api/generate-ideas."""

    num_ideas: int = Field(default=5, ge=1, le=50)
    seed_tags: Optional[list[str]] = None
    creativity: float = Field(default=0.85, ge=0.1, le=1.5)


class GenerateIdeasResponse(BaseModel):
    """Response body for POST /api/generate-ideas."""

    task_id: str
    num_requested: int
    seed_tags: list[str]


class ChatTurn(BaseModel):
    """A single turn in a text chat conversation."""

    id: int
    thread_id: str
    role: str  # user | assistant
    text: str
    source_projects: list[dict] = Field(default_factory=list)
    llm_duration_ms: Optional[int] = None
    rag_triggered: Optional[bool] = None
    agent_steps: list[dict] = Field(default_factory=list)
    created_at: datetime


class ChatThread(BaseModel):
    """A text chat conversation thread."""

    id: str
    title: str
    system_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    turns: list[ChatTurn] = Field(default_factory=list)


class VoiceTurn(BaseModel):
    """A single turn in a voice chat conversation."""

    id: int
    thread_id: str
    role: str  # user | assistant
    text: str
    audio_duration_seconds: Optional[float] = None
    tts_voice: Optional[str] = None
    token_count: Optional[int] = None
    llm_duration_ms: Optional[int] = None
    tts_duration_ms: Optional[int] = None
    stt_duration_ms: Optional[int] = None
    agent_steps: list[dict] = Field(default_factory=list)
    created_at: datetime


class VoiceThread(BaseModel):
    """A voice chat conversation thread."""

    id: str
    title: str
    system_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    turns: list[VoiceTurn] = Field(default_factory=list)
