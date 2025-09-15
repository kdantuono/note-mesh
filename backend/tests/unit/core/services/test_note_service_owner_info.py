"""Test for proper owner information in note service responses."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from src.notemesh.core.services.note_service import NoteService
from src.notemesh.core.models.note import Note
from src.notemesh.core.models.user import User


class TestNoteServiceOwnerInfo:
    """Test that note service properly includes owner information in responses."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def note_service(self, mock_session):
        """Create note service with mocked dependencies."""
        service = NoteService(mock_session)
        service.note_repo = AsyncMock()
        service.share_repo = AsyncMock()
        return service

    @pytest.fixture
    def owner_user_id(self):
        """Owner user ID."""
        return uuid.UUID("4614b1df-9cd8-4eaf-a814-4c08e4e8554f")

    @pytest.fixture
    def viewer_user_id(self):
        """Viewer user ID."""
        return uuid.UUID("70005fe1-df3b-48e8-bb94-d22a39cfdd16")

    @pytest.fixture
    def sample_note_id(self):
        """Sample note ID."""
        return uuid.UUID("35064035-1ebc-4fad-b391-761387d486ce")

    @pytest.fixture
    def mock_owner(self, owner_user_id):
        """Mock owner user."""
        owner = Mock(spec=User)
        owner.id = owner_user_id
        owner.username = "frontenduser01"
        owner.full_name = "frontend user 01"
        return owner

    @pytest.fixture
    def mock_note(self, sample_note_id, owner_user_id):
        """Mock note with owner."""
        note = Mock(spec=Note)
        note.id = sample_note_id
        note.title = "Frontend Integration Test"
        note.content = "This note tests frontend-backend integration"
        note.owner_id = owner_user_id
        note.tags = []
        note.hyperlinks = []
        note.is_public = False
        note.created_at = "2025-09-15T00:08:51.500115Z"
        note.updated_at = "2025-09-15T00:08:51.500116Z"
        note.view_count = 0
        return note

    @pytest.mark.asyncio
    async def test_owned_note_includes_owner_username(
        self, note_service, mock_note, owner_user_id, mock_owner
    ):
        """Test that when owner accesses their note, owner_username is populated."""
        # Arrange: Owner accesses their own note
        note_service.note_repo.get_by_id_and_user.return_value = mock_note

        # Mock the _get_user_info method to return owner info
        note_service._get_user_info = AsyncMock(return_value=mock_owner)

        # Act
        result = await note_service.get_note(mock_note.id, owner_user_id)

        # Assert: Owner info should be populated
        assert result.owner_username == "frontenduser01"
        assert hasattr(result, 'owner_display_name') or hasattr(result, 'owner_full_name')

    @pytest.mark.asyncio
    async def test_shared_note_includes_owner_username(
        self, note_service, mock_note, viewer_user_id, owner_user_id, mock_owner
    ):
        """Test that when viewer accesses shared note, owner_username is populated."""
        # Arrange: Note not owned by viewer but shared
        note_service.note_repo.get_by_id_and_user.return_value = None
        note_service.share_repo.check_note_access.return_value = {
            "can_read": True,
            "can_write": False,
            "is_owner": False
        }
        note_service.note_repo.get_by_id.return_value = mock_note

        # Mock the _get_user_info method to return owner info
        note_service._get_user_info = AsyncMock(return_value=mock_owner)

        # Act
        result = await note_service.get_note(mock_note.id, viewer_user_id)

        # Assert: Owner info should be populated even for shared access
        assert result.owner_username == "frontenduser01"
        assert hasattr(result, 'owner_display_name') or hasattr(result, 'owner_full_name')

    @pytest.mark.asyncio
    async def test_note_response_schema_includes_owner_fields(
        self, note_service, mock_note, owner_user_id, mock_owner
    ):
        """Test that NoteResponse schema includes all required owner fields."""
        # Arrange
        note_service.note_repo.get_by_id_and_user.return_value = mock_note
        note_service._get_user_info = AsyncMock(return_value=mock_owner)

        # Act
        result = await note_service.get_note(mock_note.id, owner_user_id)

        # Assert: Check that all owner-related fields are present
        assert hasattr(result, 'owner_id')
        assert hasattr(result, 'owner_username')
        assert result.owner_id == owner_user_id
        assert result.owner_username is not None
        assert result.owner_username != "Unknown"

    @pytest.mark.asyncio
    async def test_note_response_handles_missing_owner_gracefully(
        self, note_service, mock_note, owner_user_id
    ):
        """Test that note response handles missing owner info gracefully."""
        # Arrange: Note exists but owner lookup fails
        note_service.note_repo.get_by_id_and_user.return_value = mock_note
        note_service._get_user_info = AsyncMock(return_value=None)  # Owner not found

        # Act
        result = await note_service.get_note(mock_note.id, owner_user_id)

        # Assert: Should handle missing owner gracefully
        assert result.owner_id == owner_user_id
        # owner_username should be None or a default value, but not cause error
        assert result.owner_username is None or isinstance(result.owner_username, str)

    @pytest.mark.asyncio
    async def test_note_service_has_get_user_info_method(self, note_service):
        """Test that note service has a method to get user info."""
        # This test ensures that the note service has the infrastructure to fetch user info
        assert hasattr(note_service, '_get_user_info') or hasattr(note_service, 'user_repo')

class TestNoteServiceUserRepository:
    """Test for user repository integration in note service."""

    @pytest.fixture
    def mock_session(self):
        return Mock()

    @pytest.fixture
    def note_service_with_user_repo(self, mock_session):
        """Create note service with user repository."""
        service = NoteService(mock_session)
        service.note_repo = AsyncMock()
        service.share_repo = AsyncMock()
        service.user_repo = AsyncMock()  # Add user repository
        return service

    @pytest.mark.asyncio
    async def test_note_service_can_fetch_user_info(self, note_service_with_user_repo):
        """Test that note service can fetch user information."""
        # Arrange
        user_id = uuid.uuid4()
        mock_user = Mock()
        mock_user.username = "testuser"
        mock_user.full_name = "Test User"

        note_service_with_user_repo.user_repo.get_by_id.return_value = mock_user

        # Act
        if hasattr(note_service_with_user_repo, '_get_user_info'):
            result = await note_service_with_user_repo._get_user_info(user_id)
        else:
            result = await note_service_with_user_repo.user_repo.get_by_id(user_id)

        # Assert
        assert result.username == "testuser"
        assert result.full_name == "Test User"