"""
Note management schemas.

These schemas define the API contracts for note CRUD operations,
search functionality, and tag management.
"""

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict

from .common import PaginationResponse


class NoteCreate(BaseModel):
    """Note creation request schema."""

    title: str = Field(min_length=1, max_length=200, description="Note title")
    content: str = Field(min_length=1, description="Note content (supports Markdown)")
    tags: List[str] = Field(default_factory=list, max_length=20, description="Note tags")
    hyperlinks: List[HttpUrl] = Field(
        default_factory=list, max_length=50, description="External hyperlinks"
    )
    is_public: bool = Field(default=False, description="Whether note is publicly visible")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        """Validate tag format and uniqueness."""
        if not v:
            return v

        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate tags are not allowed")

        # Validate tag format
        tag_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
        for tag in v:
            if len(tag) < 1 or len(tag) > 30:
                raise ValueError("Tags must be between 1 and 30 characters")
            if not tag_pattern.match(tag):
                raise ValueError("Tags can only contain letters, numbers, hyphens, and underscores")

        return [tag.lower() for tag in v]  # Normalize to lowercase

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        """Validate content length."""
        if len(v.strip()) == 0:
            raise ValueError("Content cannot be empty")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Meeting Notes - Q4 Planning",
                "content": "## Agenda\n\n1. Review Q3 performance\n2. Set Q4 objectives\n\nSee also: [Company Wiki](https://wiki.company.com)",
                "tags": ["meeting", "planning", "q4"],
                "hyperlinks": [
                    "https://wiki.company.com",
                    "https://docs.google.com/spreadsheets/d/123",
                ],
                "is_public": False,
            }
        }
    )


class NoteUpdate(BaseModel):
    """Note update request schema."""

    title: Optional[str] = Field(
        default=None, min_length=1, max_length=200, description="Note title"
    )
    content: Optional[str] = Field(default=None, min_length=1, description="Note content")
    tags: Optional[List[str]] = Field(default=None, max_length=20, description="Note tags")
    hyperlinks: Optional[List[HttpUrl]] = Field(
        default=None, max_length=50, description="External hyperlinks"
    )
    is_public: Optional[bool] = Field(default=None, description="Whether note is publicly visible")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        """Validate tag format and uniqueness."""
        if v is None:
            return v

        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate tags are not allowed")

        # Validate tag format
        tag_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
        for tag in v:
            if len(tag) < 1 or len(tag) > 30:
                raise ValueError("Tags must be between 1 and 30 characters")
            if not tag_pattern.match(tag):
                raise ValueError("Tags can only contain letters, numbers, hyphens, and underscores")

        return [tag.lower() for tag in v]  # Normalize to lowercase

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        """Validate content length."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Content cannot be empty")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Meeting Notes - Q4 Planning",
                "content": "## Agenda\n\n1. Review Q3 performance ✅\n2. Set Q4 objectives\n3. Budget allocation\n\nAction items added.",
                "tags": ["meeting", "planning", "q4", "action-items"],
                "hyperlinks": ["https://wiki.company.com", "https://budget.company.com"],
            }
        }
    )


class NoteResponse(BaseModel):
    """Note response schema."""

    id: uuid.UUID = Field(description="Note unique identifier")
    title: str = Field(description="Note title")
    content: str = Field(description="Note content")
    tags: List[str] = Field(description="Note tags")
    hyperlinks: List[HttpUrl] = Field(description="External hyperlinks")
    is_public: bool = Field(description="Whether note is publicly visible")

    # Ownership and sharing info
    owner_id: uuid.UUID = Field(description="Note owner ID")
    owner_username: Optional[str] = Field(description="Note owner username")
    owner_display_name: Optional[str] = Field(description="Note owner display name")
    is_shared: bool = Field(description="Whether note is shared with current user")
    can_edit: bool = Field(description="Whether current user can edit this note")

    # Timestamps
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    # Statistics (TODO: implement in service layer)
    view_count: Optional[int] = Field(default=0, description="Number of views")
    share_count: Optional[int] = Field(default=0, description="Number of shares")

    # Sharing information for note detail view (only populated for owned notes)
    sharing_info: Optional[Dict[str, Any]] = Field(default=None, description="Detailed sharing information")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Meeting Notes - Q4 Planning",
                "content": "## Agenda\n\n1. Review Q3 performance\n2. Set Q4 objectives",
                "tags": ["meeting", "planning", "q4"],
                "hyperlinks": ["https://wiki.company.com"],
                "is_public": False,
                "owner_id": "456e7890-e89b-12d3-a456-426614174000",
                "owner_username": "john_doe",
                "is_shared": False,
                "can_edit": True,
                "created_at": "2025-09-13T10:30:00Z",
                "updated_at": "2025-09-13T11:00:00Z",
                "view_count": 15,
                "share_count": 3,
            }
        }
    )


class NoteListItem(BaseModel):
    """Simplified note schema for list views."""

    id: uuid.UUID = Field(description="Note unique identifier")
    title: str = Field(description="Note title")
    content_preview: str = Field(description="Content preview (first 200 chars)")
    tags: List[str] = Field(description="Note tags")

    # Ownership and sharing info
    owner_id: uuid.UUID = Field(description="Note owner ID")
    owner_username: Optional[str] = Field(description="Note owner username")
    owner_display_name: Optional[str] = Field(description="Note owner display name")
    is_shared: bool = Field(description="Whether note is shared with current user")
    is_owned: bool = Field(description="Whether current user owns this note")
    can_edit: bool = Field(description="Whether current user can edit this note")
    # Sharing status for owned notes
    is_shared_by_user: bool = Field(default=False, description="Whether user has shared this note with others")
    share_count: int = Field(default=0, description="Number of people this note is shared with")

    # Timestamps
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Meeting Notes - Q4 Planning",
                "content_preview": "## Agenda\n\n1. Review Q3 performance\n2. Set Q4 objectives\n\nDiscussion points: Team structure, budget allocation, timeline...",
                "tags": ["meeting", "planning", "q4"],
                "owner_id": "456e7890-e89b-12d3-a456-426614174000",
                "owner_username": "john_doe",
                "is_shared": False,
                "is_owned": True,
                "can_edit": True,
                "created_at": "2025-09-13T10:30:00Z",
                "updated_at": "2025-09-13T11:00:00Z",
            }
        }
    )


class NoteListResponse(PaginationResponse[NoteListItem]):
    """Paginated note list response."""

    # Additional aggregations (TODO: implement in service layer)
    total_owned: Optional[int] = Field(default=None, description="Total owned notes")
    total_shared: Optional[int] = Field(default=None, description="Total shared notes")
    available_tags: Optional[List[str]] = Field(
        default=None, description="Available tags for filtering"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    # NoteListItem examples here
                ],
                "total": 50,
                "page": 1,
                "per_page": 20,
                "pages": 3,
                "has_next": True,
                "has_prev": False,
                "total_owned": 30,
                "total_shared": 20,
                "available_tags": ["meeting", "planning", "personal", "work"],
            }
        }
    )


class NoteSearchRequest(BaseModel):
    """Note search request schema."""

    query: Optional[str] = Field(default=None, description="Full-text search query")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    owner_id: Optional[uuid.UUID] = Field(default=None, description="Filter by owner")
    is_public: Optional[bool] = Field(default=None, description="Filter by public/private")
    created_after: Optional[datetime] = Field(default=None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(default=None, description="Filter by creation date")
    updated_after: Optional[datetime] = Field(default=None, description="Filter by update date")
    updated_before: Optional[datetime] = Field(default=None, description="Filter by update date")

    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

    # Sorting
    sort_by: str = Field(default="updated_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        """Validate sort field."""
        allowed_fields = ["title", "created_at", "updated_at", "owner_username"]
        if v not in allowed_fields:
            raise ValueError(f'Sort field must be one of: {", ".join(allowed_fields)}')
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        """Validate sort order."""
        if v.lower() not in ["asc", "desc"]:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v.lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "meeting planning",
                "tags": ["work", "planning"],
                "is_public": False,
                "created_after": "2025-09-01T00:00:00Z",
                "page": 1,
                "per_page": 20,
                "sort_by": "updated_at",
                "sort_order": "desc",
            }
        }
    )


class NoteSearchResponse(PaginationResponse[NoteListItem]):
    """Note search results response."""

    query: Optional[str] = Field(description="Search query used")
    filters_applied: Dict[str, Any] = Field(description="Filters that were applied")
    search_time_ms: Optional[float] = Field(description="Search execution time in milliseconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    # NoteListItem examples here
                ],
                "total": 15,
                "page": 1,
                "per_page": 20,
                "pages": 1,
                "has_next": False,
                "has_prev": False,
                "query": "meeting planning",
                "filters_applied": {
                    "tags": ["work", "planning"],
                    "is_public": False,
                    "created_after": "2025-09-01T00:00:00Z",
                },
                "search_time_ms": 45.2,
            }
        }
    )
