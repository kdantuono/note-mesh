"""Test note retrieval and permissions logic following TDD approach."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from fastapi import HTTPException, status

from src.notemesh.core.services.note_service import NoteService
from src.notemesh.core.models.note import Note
from src.notemesh.core.models.share import Share, ShareStatus


class TestNoteRetrievalPermissions:
    """Test note retrieval and permission logic that caused 404/403 issues."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = Mock()
        return session

    @pytest.fixture
    def note_service(self, mock_session):
        """Create note service with mocked dependencies."""
        service = NoteService(mock_session)
        service.note_repo = AsyncMock()
        service.share_repo = AsyncMock()
        service.user_repo = AsyncMock()
        return service

    @pytest.fixture
    def sample_note_id(self):
        """Sample note ID for testing."""
        return uuid.UUID("d6b8b3fc-632b-430b-a108-cf4b045f8bef")

    @pytest.fixture
    def owner_user_id(self):
        """Owner user ID."""
        return uuid.uuid4()

    @pytest.fixture
    def other_user_id(self):
        """Non-owner user ID."""
        return uuid.uuid4()

    @pytest.fixture
    def mock_owner_user(self, owner_user_id):
        """Mock owner user."""
        from src.notemesh.core.models.user import User
        user = Mock(spec=User)
        user.id = owner_user_id
        user.username = "testowner"
        user.full_name = "Test Owner"
        return user

    @pytest.fixture
    def sample_note(self, sample_note_id, owner_user_id):
        """Create a sample note."""
        note = Mock(spec=Note)
        note.id = sample_note_id
        note.title = "Test Note"
        note.content = "Test content with link: https://example.com"
        note.owner_id = owner_user_id
        note.hyperlinks = ["https://example.com"]
        note.tags = []
        note.is_public = False
        note.created_at = "2025-09-14T23:00:00Z"
        note.updated_at = "2025-09-14T23:00:00Z"
        note.view_count = 0
        return note

    @pytest.mark.asyncio
    async def test_get_nonexistent_note_returns_404(self, note_service, sample_note_id, owner_user_id):
        """Test that accessing a non-existent note returns 404."""
        # Arrange: Note doesn't exist for owner
        note_service.note_repo.get_by_id_and_user.return_value = None
        note_service.share_repo.check_note_access.return_value = {"can_read": False}

        # Act & Assert: Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await note_service.get_note(sample_note_id, owner_user_id)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Note not found"

    @pytest.mark.asyncio
    async def test_owner_can_access_their_note(self, note_service, sample_note, owner_user_id, mock_owner_user):
        """Test that note owner can always access their note."""
        # Arrange: Owner tries to access their note
        note_service.note_repo.get_by_id_and_user.return_value = sample_note
        note_service.user_repo.get_by_id.return_value = mock_owner_user

        # Act
        result = await note_service.get_note(sample_note.id, owner_user_id)

        # Assert: Should return the note with edit permissions
        assert result.id == sample_note.id
        assert result.title == sample_note.title
        assert result.can_edit == True
        # Verify that share_repo.check_note_access was NOT called (fast path)
        note_service.share_repo.check_note_access.assert_not_called()

    @pytest.mark.asyncio
    async def test_shared_note_read_access(self, note_service, sample_note, other_user_id, mock_owner_user):
        """Test that user with read permission can access shared note."""
        # Arrange: Note not owned but shared with read permission
        note_service.note_repo.get_by_id_and_user.return_value = None
        note_service.share_repo.check_note_access.return_value = {
            "can_read": True,
            "can_write": False,
            "is_owner": False
        }
        note_service.note_repo.get_by_id.return_value = sample_note
        note_service.user_repo.get_by_id.return_value = mock_owner_user

        # Act
        result = await note_service.get_note(sample_note.id, other_user_id)

        # Assert: Should return the note with read-only permissions
        assert result.id == sample_note.id
        assert result.title == sample_note.title
        assert result.can_edit == False
        # Verify share access was checked
        note_service.share_repo.check_note_access.assert_called_once_with(sample_note.id, other_user_id)

    @pytest.mark.asyncio
    async def test_shared_note_write_access(self, note_service, sample_note, other_user_id, mock_owner_user):
        """Test that user with write permission can access and edit shared note."""
        # Arrange: Note not owned but shared with write permission
        note_service.note_repo.get_by_id_and_user.return_value = None
        note_service.share_repo.check_note_access.return_value = {
            "can_read": True,
            "can_write": True,
            "is_owner": False
        }
        note_service.note_repo.get_by_id.return_value = sample_note
        note_service.user_repo.get_by_id.return_value = mock_owner_user

        # Act
        result = await note_service.get_note(sample_note.id, other_user_id)

        # Assert: Should return the note with edit permissions
        assert result.id == sample_note.id
        assert result.title == sample_note.title
        assert result.can_edit == True

    @pytest.mark.asyncio
    async def test_no_permission_returns_404(self, note_service, sample_note_id, other_user_id):
        """Test that user without permission gets 404 (not 403 to avoid info leakage)."""
        # Arrange: Note not owned and not shared
        note_service.note_repo.get_by_id_and_user.return_value = None
        note_service.share_repo.check_note_access.return_value = {
            "can_read": False,
            "can_write": False,
            "is_owner": False
        }

        # Act & Assert: Should raise 404 (not 403 to avoid revealing note existence)
        with pytest.raises(HTTPException) as exc_info:
            await note_service.get_note(sample_note_id, other_user_id)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Note not found"

    @pytest.mark.asyncio
    async def test_shared_note_deleted_returns_404(self, note_service, sample_note_id, other_user_id):
        """Test that shared note that was deleted returns 404."""
        # Arrange: Share exists but note was deleted
        note_service.note_repo.get_by_id_and_user.return_value = None
        note_service.share_repo.check_note_access.return_value = {
            "can_read": True,
            "can_write": False,
            "is_owner": False
        }
        note_service.note_repo.get_by_id.return_value = None  # Note deleted

        # Act & Assert: Should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await note_service.get_note(sample_note_id, other_user_id)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Note not found"

    @pytest.mark.asyncio
    async def test_share_repo_exception_denies_access(self, note_service, sample_note_id, other_user_id):
        """Test that exception in share_repo.check_note_access denies access."""
        # Arrange: Note not owned and share check raises exception
        note_service.note_repo.get_by_id_and_user.return_value = None
        note_service.share_repo.check_note_access.side_effect = Exception("Database error")

        # Act & Assert: Should raise 404 (exception caught and handled)
        with pytest.raises(HTTPException) as exc_info:
            await note_service.get_note(sample_note_id, other_user_id)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Note not found"

    @pytest.mark.asyncio
    async def test_permission_field_consistency(self, note_service, sample_note, other_user_id, mock_owner_user):
        """Test that permission field is properly handled in sharing logic."""
        # Arrange: Shared note with explicit 'read' permission
        note_service.note_repo.get_by_id_and_user.return_value = None
        note_service.share_repo.check_note_access.return_value = {
            "can_read": True,
            "can_write": False,  # This should correspond to permission='read'
            "is_owner": False
        }
        note_service.note_repo.get_by_id.return_value = sample_note
        note_service.user_repo.get_by_id.return_value = mock_owner_user

        # Act
        result = await note_service.get_note(sample_note.id, other_user_id)

        # Assert: Read permission should result in can_edit=False
        assert result.can_edit == False

        # Test with write permission
        note_service.share_repo.check_note_access.return_value = {
            "can_read": True,
            "can_write": True,  # This should correspond to permission='write'
            "is_owner": False
        }

        result = await note_service.get_note(sample_note.id, other_user_id)
        assert result.can_edit == True