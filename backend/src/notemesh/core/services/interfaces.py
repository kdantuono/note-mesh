"""
Service interfaces for NoteMesh application.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from uuid import UUID

from ..schemas.auth import (
    LoginRequest, TokenResponse, RegisterRequest, UserResponse,
    RefreshTokenRequest, PasswordChangeRequest, UserUpdateRequest
)
from ..schemas.notes import (
    NoteCreate, NoteUpdate, NoteResponse, NoteListResponse,
    NoteSearchRequest, NoteSearchResponse
)
from ..schemas.sharing import (
    ShareRequest, ShareResponse, SharedNoteResponse,
    ShareListRequest, ShareListResponse, ShareStatsResponse
)
from ..schemas.common import HealthCheckResponse


class IAuthService(ABC):
    """Auth service for user management."""

    @abstractmethod
    async def register_user(self, request: RegisterRequest) -> UserResponse:
        """Register new user."""
        pass

    @abstractmethod
    async def authenticate_user(self, request: LoginRequest) -> TokenResponse:
        """Login user and return JWT tokens."""
        pass

    @abstractmethod
    async def refresh_token(self, request: RefreshTokenRequest) -> TokenResponse:
        """Refresh JWT token."""
        pass

    @abstractmethod
    async def get_current_user(self, user_id: UUID) -> UserResponse:
        """Get user by ID."""
        pass

    @abstractmethod
    async def update_user_profile(self, user_id: UUID, request: UserUpdateRequest) -> UserResponse:
        """Update user profile."""
        pass

    @abstractmethod
    async def change_password(self, user_id: UUID, request: PasswordChangeRequest) -> bool:
        """Change user password."""
        pass

    @abstractmethod
    async def logout_user(self, user_id: UUID, access_token: str) -> bool:
        """Logout user."""
        pass


class INoteService(ABC):
    """Note service for CRUD operations."""

    @abstractmethod
    async def create_note(self, user_id: UUID, request: NoteCreate) -> NoteResponse:
        """Create new note."""
        pass

    @abstractmethod
    async def get_note(self, note_id: UUID, user_id: UUID) -> NoteResponse:
        """Get note by ID."""
        pass

    @abstractmethod
    async def update_note(self, note_id: UUID, user_id: UUID, request: NoteUpdate) -> NoteResponse:
        """Update existing note."""
        pass

    @abstractmethod
    async def delete_note(self, note_id: UUID, user_id: UUID) -> bool:
        """Delete note."""
        pass

    @abstractmethod
    async def list_user_notes(
        self,
        user_id: UUID,
        page: int = 1,
        per_page: int = 20,
        tag_filter: Optional[List[str]] = None
    ) -> NoteListResponse:
        """List user notes with pagination."""
        pass

    @abstractmethod
    async def validate_hyperlinks(self, hyperlinks: List[str]) -> Dict[str, bool]:
        """Validate URLs in note content."""
        pass

    @abstractmethod
    async def get_available_tags(self, user_id: UUID) -> List[str]:
        """Get all user tags."""
        pass


class ISearchService(ABC):
    """Search service for full-text and tag filtering."""

    @abstractmethod
    async def search_notes(self, user_id: UUID, request: NoteSearchRequest) -> NoteSearchResponse:
        """Search notes with filters."""
        pass

    @abstractmethod
    async def index_note(self, note_id: UUID) -> bool:
        """Index note for search."""
        pass

    @abstractmethod
    async def remove_note_from_index(self, note_id: UUID) -> bool:
        """Remove note from search index."""
        pass

    @abstractmethod
    async def suggest_tags(self, user_id: UUID, query: str, limit: int = 10) -> List[str]:
        """Suggest tags based on query."""
        pass

    @abstractmethod
    async def get_search_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get user search stats."""
        pass


class ISharingService(ABC):
    """Note sharing service."""

    @abstractmethod
    async def share_note(self, user_id: UUID, request: ShareRequest) -> List[ShareResponse]:
        """Share note with other users."""
        pass

    @abstractmethod
    async def revoke_share(self, user_id: UUID, share_id: UUID) -> bool:
        """Revoke note share."""
        pass

    @abstractmethod
    async def get_shared_note(self, note_id: UUID, user_id: UUID) -> SharedNoteResponse:
        """Get shared note for recipient."""
        pass

    @abstractmethod
    async def list_shares(self, user_id: UUID, request: ShareListRequest) -> ShareListResponse:
        """List user shares."""
        pass

    @abstractmethod
    async def get_share_stats(self, user_id: UUID) -> ShareStatsResponse:
        """Get sharing statistics."""
        pass

    @abstractmethod
    async def check_note_access(self, note_id: UUID, user_id: UUID) -> Dict[str, bool]:
        """Check user note permissions."""
        pass


class IHealthService(ABC):
    """Health check service."""

    @abstractmethod
    async def get_health_status(self) -> HealthCheckResponse:
        """Get app health status."""
        pass

    @abstractmethod
    async def check_database_health(self) -> Dict[str, Any]:
        """Check DB connection."""
        pass

    @abstractmethod
    async def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connection."""
        pass

    @abstractmethod
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        pass