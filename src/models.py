from typing import Optional

from pydantic import BaseModel


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
