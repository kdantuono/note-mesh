"""
Note sharing schemas.

These schemas define the API contracts for note sharing functionality,
including permission management and shared note access.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
import uuid

from .common import PaginationResponse


class ShareRequest(BaseModel):
    """Note sharing request schema."""
    
    note_id: uuid.UUID = Field(description="Note ID to share")
    user_emails: List[EmailStr] = Field(
        min_items=1, 
        max_items=20, 
        description="Email addresses of users to share with"
    )
    permission: str = Field(
        default="read", 
        description="Permission level (currently only 'read' supported)"
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
    
    @validator('permission')
    def validate_permission(cls, v):
        """Validate permission level."""
        allowed_permissions = ["read"]  # As per requirements, only read permission
        if v not in allowed_permissions:
            raise ValueError(f'Permission must be one of: {", ".join(allowed_permissions)}')
        return v
    
    @validator('user_emails')
    def validate_unique_emails(cls, v):
        """Validate email uniqueness."""
        if len(v) != len(set(v)):
            raise ValueError('Duplicate email addresses are not allowed')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "note_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_emails": ["colleague@company.com", "manager@company.com"],
                "permission": "read",
                "message": "Sharing the Q4 planning notes for your review.",
                "expires_at": "2025-12-31T23:59:59Z"
            }
        }


class ShareResponse(BaseModel):
    """Note sharing response schema."""
    
    id: uuid.UUID = Field(description="Share record ID")
    note_id: uuid.UUID = Field(description="Shared note ID")
    note_title: str = Field(description="Shared note title")
    shared_with_user_id: uuid.UUID = Field(description="User ID who received the share")
    shared_with_email: EmailStr = Field(description="Email of user who received the share")
    shared_with_username: Optional[str] = Field(description="Username of user who received the share")
    permission: str = Field(description="Permission level granted")
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
    owner_username: Optional[str] = Field(description="Note owner username")
    owner_email: EmailStr = Field(description="Note owner email")
    
    # Sharing info
    shared_by_id: uuid.UUID = Field(description="User who shared the note")
    shared_by_username: Optional[str] = Field(description="Username of user who shared")
    permission: str = Field(description="Permission level for current user")
    shared_at: datetime = Field(description="When note was shared with current user")
    expires_at: Optional[datetime] = Field(description="When share expires")
    share_message: Optional[str] = Field(description="Message included with share")
    
    # Timestamps
    created_at: datetime = Field(description="Note creation timestamp")
    updated_at: datetime = Field(description="Note last update timestamp")
    last_accessed: Optional[datetime] = Field(description="Last time current user accessed this note")
    
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
    
    # Filter options
    shared_by_me: Optional[bool] = Field(default=None, description="Filter notes shared by current user")
    shared_with_me: Optional[bool] = Field(default=None, description="Filter notes shared with current user") 
    note_id: Optional[uuid.UUID] = Field(default=None, description="Filter by specific note")
    is_active: Optional[bool] = Field(default=True, description="Filter by share status")
    
    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    # Sorting
    sort_by: str = Field(default="shared_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort field."""
        allowed_fields = ["shared_at", "last_accessed", "note_title", "expires_at"]
        if v not in allowed_fields:
            raise ValueError(f'Sort field must be one of: {", ".join(allowed_fields)}')
        return v
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        """Validate sort order."""
        if v.lower() not in ["asc", "desc"]:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "shared_with_me": True,
                "is_active": True,
                "page": 1,
                "per_page": 20,
                "sort_by": "shared_at",
                "sort_order": "desc"
            }
        }


class ShareListResponse(PaginationResponse[ShareResponse]):
    """Paginated share list response."""
    
    # Additional statistics (TODO: implement in service layer)
    total_active_shares: Optional[int] = Field(description="Total active shares")
    total_expired_shares: Optional[int] = Field(description="Total expired shares")
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    # ShareResponse examples here
                ],
                "total": 25,
                "page": 1,
                "per_page": 20,
                "pages": 2,
                "has_next": True,
                "has_prev": False,
                "total_active_shares": 20,
                "total_expired_shares": 5
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
    
    total_notes_shared_by_user: int = Field(description="Total notes shared by current user")
    total_notes_shared_with_user: int = Field(description="Total notes shared with current user")
    total_active_incoming_shares: int = Field(description="Active shares received")
    total_active_outgoing_shares: int = Field(description="Active shares given")
    most_shared_tags: List[str] = Field(description="Most frequently shared tags")
    recent_share_activity: List[dict] = Field(description="Recent sharing activity")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_notes_shared_by_user": 15,
                "total_notes_shared_with_user": 8,
                "total_active_incoming_shares": 6,
                "total_active_outgoing_shares": 12,
                "most_shared_tags": ["work", "meeting", "planning"],
                "recent_share_activity": [
                    {
                        "action": "shared",
                        "note_title": "Q4 Planning",
                        "with_user": "colleague@company.com",
                        "timestamp": "2025-09-13T10:30:00Z"
                    }
                ]
            }
        }