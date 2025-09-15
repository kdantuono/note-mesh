"""Tests to increase note repository coverage."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.notemesh.core.repositories.note_repository import NoteRepository


class TestNoteRepositoryCoverage:
    """Tests to increase coverage of note repository."""

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

    @pytest.mark.asyncio
    async def test_create_note(self, note_repository, user_id):
        """Test note creation."""
        note_data = {
            "title": "Test Note",
            "content": "Test content",
            "owner_id": user_id,
            "is_public": False
        }

        # Mock the session operations
        mock_note = Mock()
        mock_note.id = uuid.uuid4()
        mock_note.title = "Test Note"

        note_repository.session.add = Mock()
        note_repository.session.commit = AsyncMock()
        note_repository.session.refresh = AsyncMock()

        # Override the Note constructor to return our mock
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("src.notemesh.core.repositories.note_repository.Note", lambda **kwargs: mock_note)

            result = await note_repository.create_note(note_data)

        assert result == mock_note
        note_repository.session.add.assert_called_once_with(mock_note)
        note_repository.session.commit.assert_called_once()
        note_repository.session.refresh.assert_called_once_with(mock_note)

    @pytest.mark.asyncio
    async def test_get_by_id(self, note_repository):
        """Test get note by ID."""
        note_id = uuid.uuid4()
        mock_note = Mock()
        mock_note.id = note_id

        # Mock the query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_note
        note_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await note_repository.get_by_id(note_id)

        assert result == mock_note
        note_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_and_user(self, note_repository, user_id):
        """Test get note by ID and user."""
        note_id = uuid.uuid4()
        mock_note = Mock()
        mock_note.id = note_id
        mock_note.owner_id = user_id

        # Mock the query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_note
        note_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await note_repository.get_by_id_and_user(note_id, user_id)

        assert result == mock_note
        note_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_note(self, note_repository, user_id):
        """Test note update."""
        note_id = uuid.uuid4()
        update_data = {"title": "Updated Title", "content": "Updated content"}

        mock_note = Mock()
        mock_note.id = note_id
        mock_note.title = "Original Title"

        # Mock get_by_id_and_user to return the note
        note_repository.get_by_id_and_user = AsyncMock(return_value=mock_note)
        note_repository.session.commit = AsyncMock()
        note_repository.session.refresh = AsyncMock()

        result = await note_repository.update_note(note_id, user_id, update_data)

        assert result == mock_note
        note_repository.session.commit.assert_called_once()
        note_repository.session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_note_not_found(self, note_repository, user_id):
        """Test update note when note not found."""
        note_id = uuid.uuid4()
        update_data = {"title": "Updated Title"}

        # Mock get_by_id_and_user to return None
        note_repository.get_by_id_and_user = AsyncMock(return_value=None)

        result = await note_repository.update_note(note_id, user_id, update_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_note_not_found(self, note_repository, user_id):
        """Test delete note when note not found."""
        note_id = uuid.uuid4()

        # Mock get_by_id_and_user to return None
        note_repository.get_by_id_and_user = AsyncMock(return_value=None)

        result = await note_repository.delete_note(note_id, user_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_note_success(self, note_repository, user_id):
        """Test successful note deletion."""
        note_id = uuid.uuid4()

        mock_note = Mock()
        mock_note.id = note_id
        mock_note.tags = []

        # Mock the operations
        note_repository.get_by_id_and_user = AsyncMock(return_value=mock_note)
        note_repository.session.delete = AsyncMock()
        note_repository.session.commit = AsyncMock()

        result = await note_repository.delete_note(note_id, user_id)

        assert result is True
        note_repository.session.delete.assert_called_once_with(mock_note)
        note_repository.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_tags(self, note_repository, user_id):
        """Test get user tags."""
        mock_result = Mock()
        mock_result.scalars.return_value = ["work", "personal", "meeting"]
        note_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await note_repository.get_user_tags(user_id)

        assert result == ["work", "personal", "meeting"]
        note_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_user_notes_with_tag_filter(self, note_repository, user_id):
        """Test list user notes with tag filter."""
        mock_notes = [Mock(), Mock()]
        mock_total = 5

        # Mock count query result
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = mock_total

        # Mock notes query result
        mock_notes_result = Mock()
        mock_notes_result.scalars.return_value.all.return_value = mock_notes

        # Session execute returns different results for different calls
        note_repository.session.execute = AsyncMock(side_effect=[mock_count_result, mock_notes_result])

        result_notes, result_total = await note_repository.list_user_notes(
            user_id, page=1, per_page=20, tag_filter=["work"]
        )

        assert result_notes == mock_notes
        assert result_total == mock_total
        assert note_repository.session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_list_user_notes_without_tag_filter(self, note_repository, user_id):
        """Test list user notes without tag filter."""
        mock_notes = [Mock(), Mock()]
        mock_total = 3

        # Mock count query result
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = mock_total

        # Mock notes query result
        mock_notes_result = Mock()
        mock_notes_result.scalars.return_value.all.return_value = mock_notes

        note_repository.session.execute = AsyncMock(side_effect=[mock_count_result, mock_notes_result])

        result_notes, result_total = await note_repository.list_user_notes(
            user_id, page=2, per_page=10, tag_filter=None
        )

        assert result_notes == mock_notes
        assert result_total == mock_total
        assert note_repository.session.execute.call_count == 2