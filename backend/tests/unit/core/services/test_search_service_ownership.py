"""TDD tests for search service ownership display."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.notemesh.core.services.search_service import SearchService
from src.notemesh.core.schemas.notes import NoteSearchRequest


class TestSearchServiceOwnership:
    """Test search service correctly identifies note ownership for display."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def search_service(self, mock_session):
        """Create search service with mocked dependencies."""
        service = SearchService(mock_session)
        service.note_repo = AsyncMock()
        return service

    @pytest.fixture
    def user_id(self):
        """Sample user ID."""
        return uuid.uuid4()

    @pytest.fixture
    def other_user_id(self):
        """Another user ID."""
        return uuid.uuid4()

    @pytest.fixture
    def mock_owned_note(self, user_id):
        """Mock note owned by current user."""
        note = Mock()
        note.id = uuid.uuid4()
        note.title = "My Note"
        note.content = "Content I wrote"
        note.owner_id = user_id  # User owns this note
        note.created_at = datetime.utcnow()
        note.updated_at = datetime.utcnow()
        note.tags = []
        return note

    @pytest.fixture
    def mock_shared_note(self, other_user_id):
        """Mock note shared with current user."""
        note = Mock()
        note.id = uuid.uuid4()
        note.title = "Shared Note"
        note.content = "Content shared with me"
        note.owner_id = other_user_id  # Someone else owns this note
        note.created_at = datetime.utcnow()
        note.updated_at = datetime.utcnow()
        note.tags = []
        return note

    @pytest.mark.asyncio
    async def test_search_owned_note_shows_correct_ownership(
        self, search_service, user_id, mock_owned_note
    ):
        """Test that owned notes show correct ownership in search results."""
        # Setup
        search_service.note_repo.search_notes.return_value = [mock_owned_note]

        request = NoteSearchRequest(
            query="note",
            tags=None,
            page=1,
            per_page=20
        )

        # Act
        result = await search_service.search_notes(user_id, request)

        # Assert
        assert len(result.items) == 1
        note_item = result.items[0]

        # Should show as owned
        assert note_item.is_owned == True
        assert note_item.is_shared == False
        assert note_item.can_edit == True
        assert note_item.owner_id == user_id

    @pytest.mark.asyncio
    async def test_search_shared_note_shows_correct_ownership(
        self, search_service, user_id, mock_shared_note, other_user_id
    ):
        """Test that shared notes show correct ownership in search results."""
        # Setup
        search_service.note_repo.search_notes.return_value = [mock_shared_note]

        request = NoteSearchRequest(
            query="note",
            tags=None,
            page=1,
            per_page=20
        )

        # Act
        result = await search_service.search_notes(user_id, request)

        # Assert
        assert len(result.items) == 1
        note_item = result.items[0]

        # Should show as shared (not owned)
        assert note_item.is_owned == False
        assert note_item.is_shared == True
        assert note_item.can_edit == False  # Default read-only access
        assert note_item.owner_id == other_user_id

    @pytest.mark.asyncio
    async def test_search_mixed_notes_shows_correct_ownership(
        self, search_service, user_id, mock_owned_note, mock_shared_note, other_user_id
    ):
        """Test that search with mixed owned/shared notes shows correct ownership."""
        # Setup
        search_service.note_repo.search_notes.return_value = [mock_owned_note, mock_shared_note]

        request = NoteSearchRequest(
            query="note",
            tags=None,
            page=1,
            per_page=20
        )

        # Act
        result = await search_service.search_notes(user_id, request)

        # Assert
        assert len(result.items) == 2

        # Find owned and shared notes
        owned_note = next((item for item in result.items if item.owner_id == user_id), None)
        shared_note = next((item for item in result.items if item.owner_id == other_user_id), None)

        assert owned_note is not None
        assert shared_note is not None

        # Owned note assertions
        assert owned_note.is_owned == True
        assert owned_note.is_shared == False
        assert owned_note.can_edit == True

        # Shared note assertions
        assert shared_note.is_owned == False
        assert shared_note.is_shared == True
        assert shared_note.can_edit == False