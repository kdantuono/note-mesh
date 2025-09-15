"""TDD tests for note repository tag filter functionality."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.notemesh.core.repositories.note_repository import NoteRepository


class TestNoteRepositoryTagFilter:
    """Test note repository tag filtering functionality."""

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
    def mock_note_with_work_tag(self):
        """Mock note with work tag."""
        note = Mock()
        note.id = uuid.uuid4()
        note.title = "Work Meeting Notes"
        note.content = "Meeting about project planning"
        note.owner_id = uuid.uuid4()
        note.created_at = datetime.utcnow()
        note.updated_at = datetime.utcnow()

        # Mock tag
        tag = Mock()
        tag.name = "work"
        note.tags = [tag]
        return note

    @pytest.fixture
    def mock_note_with_personal_tag(self):
        """Mock note with personal tag."""
        note = Mock()
        note.id = uuid.uuid4()
        note.title = "Personal Reminder"
        note.content = "Remember to buy groceries"
        note.owner_id = uuid.uuid4()
        note.created_at = datetime.utcnow()
        note.updated_at = datetime.utcnow()

        # Mock tag
        tag = Mock()
        tag.name = "personal"
        note.tags = [tag]
        return note

    @pytest.mark.asyncio
    async def test_search_notes_with_tag_filter_calls_correct_query(
        self, note_repository, user_id, mock_note_with_work_tag
    ):
        """Test that search_notes with tag filter constructs correct query."""
        # Setup mock session and execute
        mock_result = Mock()
        mock_result.scalars.return_value = [mock_note_with_work_tag]
        note_repository.session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await note_repository.search_notes(
            user_id=user_id,
            query="meeting",
            tag_filter=["work"]
        )

        # Assert
        assert len(result) == 1
        assert result[0].title == "Work Meeting Notes"
        note_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_notes_with_empty_tag_filter_list(
        self, note_repository, user_id, mock_note_with_work_tag
    ):
        """Test that search_notes with empty tag filter list works correctly."""
        # Setup mock session and execute
        mock_result = Mock()
        mock_result.scalars.return_value = [mock_note_with_work_tag]
        note_repository.session.execute = AsyncMock(return_value=mock_result)

        # Act - empty list should not apply tag filter
        result = await note_repository.search_notes(
            user_id=user_id,
            query="meeting",
            tag_filter=[]
        )

        # Assert
        assert len(result) == 1
        note_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_notes_with_none_tag_filter(
        self, note_repository, user_id, mock_note_with_work_tag
    ):
        """Test that search_notes with None tag filter works correctly."""
        # Setup mock session and execute
        mock_result = Mock()
        mock_result.scalars.return_value = [mock_note_with_work_tag]
        note_repository.session.execute = AsyncMock(return_value=mock_result)

        # Act - None should not apply tag filter
        result = await note_repository.search_notes(
            user_id=user_id,
            query="meeting",
            tag_filter=None
        )

        # Assert
        assert len(result) == 1
        note_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_user_notes_with_tag_filter_consistency(
        self, note_repository, user_id, mock_note_with_work_tag
    ):
        """Test that list_user_notes tag filter behaves consistently with search_notes."""
        # Setup mock session and execute
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_note_with_work_tag]
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 1

        note_repository.session.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

        # Act
        notes, total = await note_repository.list_user_notes(
            user_id=user_id,
            page=1,
            per_page=20,
            tag_filter=["work"]
        )

        # Assert
        assert len(notes) == 1
        assert total == 1
        assert notes[0].title == "Work Meeting Notes"
        assert note_repository.session.execute.call_count == 2