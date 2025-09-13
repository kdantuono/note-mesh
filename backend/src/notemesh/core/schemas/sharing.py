"""
Note sharing schemas.

These schemas define the API contracts for note sharing functionality,
including permission management and shared note access.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import datetime
import uuid

from .common import PaginationResponse


class ShareRequest(BaseModel):
    """Note sharing request schema."""
    
    note_id: uuid.UUID = Field(description="Note ID to share")
    shared_with_usernames: List[str] = Field(
        min_items=1,
        max_items=20,
        description="Usernames of users to share with"
    )
    permission_level: str = Field(
        default="read",
        description="Permission level (read or write)"
    )
    message: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional message to include with share notification"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Optional expiration date for the share"
    )
    
    @field_validator('permission_level')
    @classmethod
    def validate_permission_level(cls, v):
        """Validate permission level."""
        allowed_permissions = ["read", "write"]
        if v not in allowed_permissions:
            raise ValueError(f'Permission level must be one of: {", ".join(allowed_permissions)}')
        return v

    @field_validator('shared_with_usernames')
    @classmethod
    def validate_unique_usernames(cls, v):
        """Validate username uniqueness."""
        if len(v) != len(set(v)):
            raise ValueError('Duplicate usernames are not allowed')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "note_id": "123e4567-e89b-12d3-a456-426614174000",
                "shared_with_usernames": ["colleague", "manager"],
                "permission_level": "read",
                "message": "Sharing the Q4 planning notes for your review."
            }
        }


class ShareResponse(BaseModel):
    """Note sharing response schema."""
    
    id: uuid.UUID = Field(description="Share record ID")
    note_id: uuid.UUID = Field(description="Shared note ID")
    note_title: str = Field(description="Shared note title")
    shared_with_user_id: uuid.UUID = Field(description="User ID who received the share")
    shared_with_username: str = Field(description="Username of user who received the share")
    shared_with_display_name: str = Field(description="Display name of user who received the share")
    permission_level: str = Field(description="Permission level granted")
    message: Optional[str] = Field(description="Message included with share")
    
    # Timestamps
    shared_at: datetime = Field(description="When the note was shared")
    expires_at: Optional[datetime] = Field(description="When the share expires")
    last_accessed: Optional[datetime] = Field(description="Last time shared note was accessed")
    
    # Status
    is_active: bool = Field(description="Whether the share is currently active")
    access_count: int = Field(default=0, description="Number of times shared note was accessed")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "789e0123-e89b-12d3-a456-426614174000",
                "note_id": "123e4567-e89b-12d3-a456-426614174000",
                "note_title": "Q4 Planning Notes",
                "shared_with_user_id": "456e7890-e89b-12d3-a456-426614174000",
                "shared_with_email": "colleague@company.com",
                "shared_with_username": "colleague",
                "permission": "read",
                "message": "Sharing the Q4 planning notes for your review.",
                "shared_at": "2025-09-13T10:30:00Z",
                "expires_at": "2025-12-31T23:59:59Z",
                "last_accessed": "2025-09-13T14:20:00Z",
                "is_active": True,
                "access_count": 5
            }
        }


class SharedNoteResponse(BaseModel):
    """Shared note response schema for recipients."""
    
    id: uuid.UUID = Field(description="Note ID")
    title: str = Field(description="Note title")
    content: str = Field(description="Note content")
    tags: List[str] = Field(description="Note tags")
    hyperlinks: List[str] = Field(description="External hyperlinks")
    
    # Original note info
    owner_id: uuid.UUID = Field(description="Note owner ID")
    owner_username: str = Field(description="Note owner username")
    owner_display_name: str = Field(description="Note owner display name")
    
    # Sharing info
    shared_by_id: uuid.UUID = Field(description="User who shared the note")
    shared_by_username: str = Field(description="Username of user who shared")
    permission_level: str = Field(description="Permission level for current user")
    shared_at: datetime = Field(description="When note was shared with current user")
    expires_at: Optional[datetime] = Field(description="When share expires")
    share_message: Optional[str] = Field(description="Message included with share")
    
    # Timestamps
    created_at: datetime = Field(description="Note creation timestamp")
    updated_at: datetime = Field(description="Note last update timestamp")
    last_accessed: Optional[datetime] = Field(description="Last time current user accessed this note")

    # Access permissions
    can_write: bool = Field(description="Whether user can edit this note")
    can_share: bool = Field(description="Whether user can share this note")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Q4 Planning Notes",
                "content": "## Agenda\n\n1. Review Q3 performance\n2. Set Q4 objectives",
                "tags": ["planning", "q4", "meeting"],
                "hyperlinks": ["https://wiki.company.com"],
                "owner_id": "999e8888-e89b-12d3-a456-426614174000",
                "owner_username": "team_lead",
                "owner_email": "lead@company.com",
                "shared_by_id": "999e8888-e89b-12d3-a456-426614174000",
                "shared_by_username": "team_lead",
                "permission": "read",
                "shared_at": "2025-09-13T10:30:00Z",
                "expires_at": "2025-12-31T23:59:59Z",
                "share_message": "Please review for tomorrow's meeting",
                "created_at": "2025-09-12T09:00:00Z",
                "updated_at": "2025-09-13T08:15:00Z",
                "last_accessed": "2025-09-13T14:20:00Z"
            }
        }


class ShareListRequest(BaseModel):
    """Request schema for listing shared notes."""

    # Type of shares to list
    type: Optional[str] = Field(default="given", description="Type of shares to list (given or received)")

    # Pagination
    page: Optional[int] = Field(default=1, ge=1, description="Page number")
    per_page: Optional[int] = Field(default=20, ge=1, le=100, description="Items per page")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "received",
                "page": 1,
                "per_page": 20
            }
        }


class ShareListResponse(BaseModel):
    """Paginated share list response."""

    shares: List[ShareResponse] = Field(description="List of shares")
    total_count: int = Field(description="Total number of shares")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")
    type: str = Field(description="Type of shares listed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shares": [],
                "total_count": 25,
                "page": 1,
                "per_page": 20,
                "total_pages": 2,
                "type": "given"
            }
        }


class RevokeShareRequest(BaseModel):
    """Request schema for revoking a share."""
    
    share_id: uuid.UUID = Field(description="Share ID to revoke")
    reason: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional reason for revoking share"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "share_id": "789e0123-e89b-12d3-a456-426614174000",
                "reason": "Project completed, no longer need access"
            }
        }


class ShareStatsResponse(BaseModel):
    """Share statistics response schema."""

    shares_given: int = Field(description="Total shares created by user")
    shares_received: int = Field(description="Total shares received by user")
    unique_notes_shared: int = Field(description="Number of unique notes shared by user")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shares_given": 15,
                "shares_received": 8,
                "unique_notes_shared": 10
            }
        }