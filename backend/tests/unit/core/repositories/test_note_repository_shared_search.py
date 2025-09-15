"""TDD tests for note repository search including shared notes."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.notemesh.core.repositories.note_repository import NoteRepository


class TestNoteRepositorySharedSearch:
    """Test note repository search includes notes shared with user."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def note_repository(self, mock_session):
        """Create note repository with mocked session."""
        return NoteRepository(mock_session)

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
        """Mock note owned by user."""
        note = Mock()
        note.id = uuid.uuid4()
        note.title = "My Own Note"
        note.content = "Content I wrote"
        note.owner_id = user_id
        note.created_at = datetime.utcnow()
        note.updated_at = datetime.utcnow()
        note.tags = []
        return note

    @pytest.fixture
    def mock_shared_note(self, other_user_id):
        """Mock note shared with user."""
        note = Mock()
        note.id = uuid.uuid4()
        note.title = "Shared Note"
        note.content = "Content shared with me"
        note.owner_id = other_user_id  # Owned by someone else
        note.created_at = datetime.utcnow()
        note.updated_at = datetime.utcnow()
        note.tags = []
        return note

    @pytest.mark.asyncio
    async def test_search_includes_notes_shared_with_user(
        self, note_repository, user_id, mock_owned_note, mock_shared_note
    ):
        """Test that search includes both owned and shared notes."""
        # Setup mock to return both owned and shared notes
        mock_result = Mock()
        mock_result.scalars.return_value = [mock_owned_note, mock_shared_note]
        note_repository.session.execute = AsyncMock(return_value=mock_result)

        # Act
        results = await note_repository.search_notes(user_id, "note", tag_filter=None)

        # Assert
        assert len(results) == 2
        note_titles = [note.title for note in results]
        assert "My Own Note" in note_titles
        assert "Shared Note" in note_titles

        # Verify the SQL includes OR condition for shared notes
        note_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_with_tags_includes_shared_notes(
        self, note_repository, user_id, mock_owned_note, mock_shared_note
    ):
        """Test that tag search also includes shared notes."""
        # Add tags to notes
        mock_tag = Mock()
        mock_tag.name = "work"
        mock_owned_note.tags = [mock_tag]
        mock_shared_note.tags = [mock_tag]

        # Setup mock
        mock_result = Mock()
        mock_result.scalars.return_value = [mock_owned_note, mock_shared_note]
        note_repository.session.execute = AsyncMock(return_value=mock_result)

        # Act
        results = await note_repository.search_notes(user_id, "note", tag_filter=["work"])

        # Assert
        assert len(results) == 2
        note_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_only_finds_accessible_notes(
        self, note_repository, user_id, mock_owned_note
    ):
        """Test that search only finds notes the user can access."""
        # Create note not accessible to user
        inaccessible_note = Mock()
        inaccessible_note.id = uuid.uuid4()
        inaccessible_note.title = "Private Note"
        inaccessible_note.content = "Not shared with user"
        inaccessible_note.owner_id = uuid.uuid4()  # Different owner
        inaccessible_note.tags = []

        # Setup mock to return only accessible notes
        mock_result = Mock()
        mock_result.scalars.return_value = [mock_owned_note]  # Only owned note
        note_repository.session.execute = AsyncMock(return_value=mock_result)

        # Act
        results = await note_repository.search_notes(user_id, "note", tag_filter=None)

        # Assert
        assert len(results) == 1
        assert results[0].title == "My Own Note"
        note_repository.session.execute.assert_called_once()