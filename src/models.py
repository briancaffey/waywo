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
    source_comment_id: int

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


class WaywoProjectSummary(BaseModel):
    """Summary of a WaywoProject for list views."""

    id: int
    source_comment_id: int
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
