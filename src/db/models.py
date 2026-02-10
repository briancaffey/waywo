"""
SQLAlchemy ORM models for waywo database.
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


class WaywoPostDB(Base):
    """SQLAlchemy model for Hacker News 'What are you working on?' posts."""

    __tablename__ = "waywo_posts"

    # Primary key - using HN item ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # HN item fields
    type: Mapped[str] = mapped_column(String(50), default="story")
    by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dead: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    deleted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    kids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # Post-specific fields
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    descendants: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata from waywo.yml
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    comments: Mapped[list["WaywoCommentDB"]] = relationship(
        "WaywoCommentDB", back_populates="parent_post"
    )

    __table_args__ = (Index("ix_waywo_posts_year_month", "year", "month"),)

    def get_kids_list(self) -> list[int]:
        """Parse kids JSON string to list of integers."""
        if self.kids is None:
            return []
        return json.loads(self.kids)

    def set_kids_list(self, kids: list[int]) -> None:
        """Serialize list of integers to JSON string."""
        self.kids = json.dumps(kids) if kids else None


class WaywoCommentDB(Base):
    """SQLAlchemy model for top-level comments on WaywoPost entries."""

    __tablename__ = "waywo_comments"

    # Primary key - using HN item ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # HN item fields
    type: Mapped[str] = mapped_column(String(50), default="comment")
    by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dead: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    deleted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    kids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    # Comment-specific fields
    parent: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("waywo_posts.id"), nullable=True
    )

    # Processing status
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    parent_post: Mapped[Optional["WaywoPostDB"]] = relationship(
        "WaywoPostDB", back_populates="comments"
    )
    projects: Mapped[list["WaywoProjectDB"]] = relationship(
        "WaywoProjectDB", back_populates="source_comment"
    )

    __table_args__ = (
        Index("ix_waywo_comments_parent", "parent"),
        Index("ix_waywo_comments_processed", "processed"),
        Index("ix_waywo_comments_by", "by"),
    )

    def get_kids_list(self) -> list[int]:
        """Parse kids JSON string to list of integers."""
        if self.kids is None:
            return []
        return json.loads(self.kids)

    def set_kids_list(self, kids: list[int]) -> None:
        """Serialize list of integers to JSON string."""
        self.kids = json.dumps(kids) if kids else None


class WaywoProjectDB(Base):
    """SQLAlchemy model for extracted project data from comments."""

    __tablename__ = "waywo_projects"

    # Auto-generated primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Link to source comment
    source_comment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("waywo_comments.id"), nullable=False
    )

    # Validation status
    is_valid_project: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    invalid_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Core metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    short_description: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array

    # URLs and scraped content
    project_urls: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array
    url_summaries: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON dict
    primary_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url_contents: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON dict

    # Scores (1-10)
    idea_score: Mapped[int] = mapped_column(Integer, nullable=False)
    complexity_score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Workflow metadata
    workflow_logs: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array

    # Vector embedding for semantic search
    description_embedding: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, nullable=True
    )  # FLOAT32 vector blob

    # Bookmarking
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Screenshot
    screenshot_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # UMAP cluster map coordinates
    umap_x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    umap_y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cluster_label: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    source_comment: Mapped["WaywoCommentDB"] = relationship(
        "WaywoCommentDB", back_populates="projects"
    )

    __table_args__ = (
        Index("ix_waywo_projects_source_comment_id", "source_comment_id"),
        Index("ix_waywo_projects_idea_score", "idea_score"),
        Index("ix_waywo_projects_complexity_score", "complexity_score"),
        Index("ix_waywo_projects_is_valid", "is_valid_project"),
        Index("ix_waywo_projects_created_at", "created_at"),
    )

    # JSON field helpers
    def get_hashtags_list(self) -> list[str]:
        """Parse hashtags JSON string to list."""
        if self.hashtags is None:
            return []
        return json.loads(self.hashtags)

    def set_hashtags_list(self, tags: list[str]) -> None:
        """Serialize list to JSON string."""
        self.hashtags = json.dumps(tags)

    def get_project_urls_list(self) -> list[str]:
        """Parse project_urls JSON string to list."""
        if self.project_urls is None:
            return []
        return json.loads(self.project_urls)

    def set_project_urls_list(self, urls: list[str]) -> None:
        """Serialize list to JSON string."""
        self.project_urls = json.dumps(urls) if urls else None

    def get_url_summaries_dict(self) -> dict[str, str]:
        """Parse url_summaries JSON string to dict."""
        if self.url_summaries is None:
            return {}
        return json.loads(self.url_summaries)

    def set_url_summaries_dict(self, summaries: dict[str, str]) -> None:
        """Serialize dict to JSON string."""
        self.url_summaries = json.dumps(summaries) if summaries else None

    def get_url_contents_dict(self) -> dict[str, str]:
        """Parse url_contents JSON string to dict."""
        if self.url_contents is None:
            return {}
        return json.loads(self.url_contents)

    def set_url_contents_dict(self, contents: dict[str, str]) -> None:
        """Serialize dict to JSON string."""
        self.url_contents = json.dumps(contents) if contents else None

    def get_workflow_logs_list(self) -> list[str]:
        """Parse workflow_logs JSON string to list."""
        if self.workflow_logs is None:
            return []
        return json.loads(self.workflow_logs)

    def set_workflow_logs_list(self, logs: list[str]) -> None:
        """Serialize list to JSON string."""
        self.workflow_logs = json.dumps(logs) if logs else None


class WaywoVideoDB(Base):
    """SQLAlchemy model for generated project videos."""

    __tablename__ = "waywo_videos"

    # Auto-generated primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Link to source project
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("waywo_projects.id"), nullable=False
    )

    # Version tracking (auto-increment per project to keep old videos)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Script metadata (from LLM)
    video_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    script_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Full LLM output

    # Voice used for TTS
    voice_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Generation status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending | script_generated | generating | completed | failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Output paths
    video_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Video metadata
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width: Mapped[int] = mapped_column(Integer, default=1080, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=1920, nullable=False)

    # Workflow logs
    workflow_logs: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array

    # User interaction
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_favorited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    project: Mapped["WaywoProjectDB"] = relationship("WaywoProjectDB", backref="videos")
    segments: Mapped[list["WaywoVideoSegmentDB"]] = relationship(
        "WaywoVideoSegmentDB",
        back_populates="video",
        order_by="WaywoVideoSegmentDB.segment_index",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_waywo_videos_project_id", "project_id"),
        Index("ix_waywo_videos_status", "status"),
        Index("ix_waywo_videos_created_at", "created_at"),
    )

    def get_workflow_logs_list(self) -> list[str]:
        """Parse workflow_logs JSON string to list."""
        if self.workflow_logs is None:
            return []
        return json.loads(self.workflow_logs)

    def set_workflow_logs_list(self, logs: list[str]) -> None:
        """Serialize list to JSON string."""
        self.workflow_logs = json.dumps(logs) if logs else None


class WaywoVideoSegmentDB(Base):
    """SQLAlchemy model for individual segments within a video."""

    __tablename__ = "waywo_video_segments"

    # Auto-generated primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Link to parent video
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("waywo_videos.id"), nullable=False
    )

    # Ordering
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Script data (from LLM)
    segment_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # hook | introduction | features | audience | closing
    narration_text: Mapped[str] = mapped_column(Text, nullable=False)
    scene_description: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Original from LLM
    image_prompt: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Editable, defaults to scene_description
    visual_style: Mapped[str] = mapped_column(
        String(50), default="abstract", nullable=False
    )  # abstract | screenshot | text_overlay
    transition: Mapped[str] = mapped_column(
        String(50), default="fade", nullable=False
    )  # fade | cut | slide_left | zoom_in

    # Audio data
    audio_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # Image data
    image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_name: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # InvokeAI image name

    # Transcription data (word-level timestamps)
    transcription_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON: {"text": "...", "words": [...]}

    # Segment generation status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending | audio_generated | image_generated | complete | failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    video: Mapped["WaywoVideoDB"] = relationship(
        "WaywoVideoDB", back_populates="segments"
    )

    __table_args__ = (
        Index("ix_waywo_video_segments_video_id", "video_id"),
        Index("ix_waywo_video_segments_status", "status"),
    )

    def get_transcription_dict(self) -> dict | None:
        """Parse transcription_json to dict."""
        if self.transcription_json is None:
            return None
        return json.loads(self.transcription_json)

    def set_transcription_dict(self, data: dict | None) -> None:
        """Serialize dict to JSON string."""
        self.transcription_json = json.dumps(data) if data else None


class VoiceThreadDB(Base):
    """SQLAlchemy model for voice chat threads."""

    __tablename__ = "voice_threads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(Text, default="New conversation", nullable=False)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    turns: Mapped[list["VoiceTurnDB"]] = relationship(
        "VoiceTurnDB",
        back_populates="thread",
        order_by="VoiceTurnDB.created_at",
        cascade="all, delete-orphan",
    )


class VoiceTurnDB(Base):
    """SQLAlchemy model for individual turns within a voice chat thread."""

    __tablename__ = "voice_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("voice_threads.id", ondelete="CASCADE"), nullable=False
    )

    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    text: Mapped[str] = mapped_column(Text, nullable=False)

    audio_duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    tts_voice: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    stt_raw_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tts_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stt_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    thread: Mapped["VoiceThreadDB"] = relationship(
        "VoiceThreadDB", back_populates="turns"
    )

    __table_args__ = (
        Index("ix_voice_turns_thread_id", "thread_id"),
        Index("ix_voice_turns_thread_created", "thread_id", "created_at"),
    )
