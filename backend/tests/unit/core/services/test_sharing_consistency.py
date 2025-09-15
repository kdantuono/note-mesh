"""Test for consistent error handling between note service and sharing service."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from fastapi import HTTPException, status

from src.notemesh.core.services.sharing_service import SharingService


class TestSharingConsistency:
    """Test consistent error handling across note and sharing endpoints."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def sharing_service(self, mock_session):
        """Create sharing service with mocked dependencies."""
        service = SharingService(mock_session)
        service.share_repo = AsyncMock()
        service.note_repo = AsyncMock()
        service.user_repo = AsyncMock()
        return service

    @pytest.fixture
    def nonexistent_note_id(self):
        """Non-existent note ID for testing."""
        return uuid.UUID("d6b8b3fc-632b-430b-a108-cf4b045f8bef")

    @pytest.fixture
    def user_id(self):
        """User ID for testing."""
        return uuid.uuid4()

    @pytest.mark.asyncio
    async def test_get_shared_note_nonexistent_returns_404_not_403(
        self, sharing_service, nonexistent_note_id, user_id
    ):
        """Test that get_shared_note returns 404 for non-existent notes, not 403.

        This ensures consistent behavior with NoteService.get_note() and prevents
        information leakage about note existence.
        """
        # Arrange: No access to non-existent note
        sharing_service.share_repo.check_note_access.return_value = {
            "can_read": False,
            "can_write": False,
            "is_owner": False
        }

        # Act & Assert: Should raise 404, not 403
        # The current implementation incorrectly raises 403
        with pytest.raises(HTTPException) as exc_info:
            await sharing_service.get_shared_note(nonexistent_note_id, user_id)

        # This test will initially fail because current implementation returns 403
        # After fixing, it should pass with 404
        expected_status = status.HTTP_404_NOT_FOUND
        expected_detail = "Note not found"

        assert exc_info.value.status_code == expected_status
        assert exc_info.value.detail == expected_detail

    @pytest.mark.asyncio
    async def test_get_shared_note_with_access_works(
        self, sharing_service, nonexistent_note_id, user_id
    ):
        """Test that get_shared_note works when user has access."""
        # Arrange: User has read access
        sharing_service.share_repo.check_note_access.return_value = {
            "can_read": True,
            "can_write": False,
            "is_owner": False
        }

        # Mock note exists
        mock_note = Mock()
        mock_note.id = nonexistent_note_id
        mock_note.title = "Shared Note"
        mock_note.content = "Shared content"
        mock_note.owner_id = uuid.uuid4()
        mock_note.hyperlinks = []
        mock_note.tags = []
        mock_note.created_at = "2025-09-14T23:00:00Z"
        mock_note.updated_at = "2025-09-14T23:00:00Z"

        sharing_service.note_repo.get_by_id.return_value = mock_note

        # Mock owner info
        mock_owner = Mock()
        mock_owner.username = "owner_user"
        mock_owner.full_name = "Owner User"
        sharing_service.user_repo.get_by_id.return_value = mock_owner

        # Act
        result = await sharing_service.get_shared_note(nonexistent_note_id, user_id)

        # Assert: Should work and return the note
        assert result is not None
        # The exact structure depends on SharedNoteResponse implementation

    @pytest.mark.asyncio
    async def test_check_note_access_consistency(
        self, sharing_service, nonexistent_note_id, user_id
    ):
        """Test that check_note_access returns consistent results."""
        # Arrange: No access to note
        sharing_service.share_repo.check_note_access.return_value = {
            "can_read": False,
            "can_write": False,
            "can_share": False,
            "is_owner": False
        }

        # Act
        result = await sharing_service.check_note_access(nonexistent_note_id, user_id)

        # Assert: Should return the permission dict
        assert result["can_read"] is False
        assert result["can_write"] is False
        assert result["can_share"] is False
        assert result["is_owner"] is False