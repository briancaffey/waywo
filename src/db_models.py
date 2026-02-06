"""
SQLAlchemy ORM models for waywo database.
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


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

    def get_workflow_logs_list(self) -> list[str]:
        """Parse workflow_logs JSON string to list."""
        if self.workflow_logs is None:
            return []
        return json.loads(self.workflow_logs)

    def set_workflow_logs_list(self, logs: list[str]) -> None:
        """Serialize list to JSON string."""
        self.workflow_logs = json.dumps(logs) if logs else None
