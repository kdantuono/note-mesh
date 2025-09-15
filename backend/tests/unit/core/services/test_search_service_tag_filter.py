"""TDD tests for search service tag filter functionality."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.notemesh.core.services.search_service import SearchService
from src.notemesh.core.schemas.notes import NoteSearchRequest


class TestSearchServiceTagFilter:
    """Test search service tag filtering functionality."""

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
    def mock_tag_work(self):
        """Mock work tag."""
        tag = Mock()
        tag.name = "work"
        return tag

    @pytest.fixture
    def mock_tag_personal(self):
        """Mock personal tag."""
        tag = Mock()
        tag.name = "personal"
        return tag

    @pytest.fixture
    def mock_note_with_work_tag(self, mock_tag_work):
        """Mock note with work tag."""
        note = Mock()
        note.id = uuid.uuid4()
        note.title = "Work Meeting Notes"
        note.content = "Meeting about project planning"
        note.owner_id = uuid.uuid4()
        note.created_at = datetime.utcnow()
        note.updated_at = datetime.utcnow()
        note.tags = [mock_tag_work]
        return note

    @pytest.fixture
    def mock_note_with_personal_tag(self, mock_tag_personal):
        """Mock note with personal tag."""
        note = Mock()
        note.id = uuid.uuid4()
        note.title = "Personal Reminder"
        note.content = "Remember to buy groceries"
        note.owner_id = uuid.uuid4()
        note.created_at = datetime.utcnow()
        note.updated_at = datetime.utcnow()
        note.tags = [mock_tag_personal]
        return note

    @pytest.fixture
    def mock_note_no_tags(self):
        """Mock note without tags."""
        note = Mock()
        note.id = uuid.uuid4()
        note.title = "Untagged Note"
        note.content = "This note has no tags"
        note.owner_id = uuid.uuid4()
        note.created_at = datetime.utcnow()
        note.updated_at = datetime.utcnow()
        note.tags = []
        return note

    @pytest.mark.asyncio
    async def test_search_with_tag_filter_returns_only_matching_notes(
        self, search_service, user_id, mock_note_with_work_tag, mock_note_with_personal_tag, mock_note_no_tags
    ):
        """Test that tag filter returns only notes with matching tags."""
        # Arrange
        all_notes = [mock_note_with_work_tag, mock_note_with_personal_tag, mock_note_no_tags]
        work_filtered_notes = [mock_note_with_work_tag]  # Only work-tagged note

        # Mock repository to return work-tagged note when filtering by "work"
        search_service.note_repo.search_notes.return_value = work_filtered_notes

        request = NoteSearchRequest(
            query="meeting",  # Text that should match
            tags=["work"],    # Filter by work tag
            page=1,
            per_page=20
        )

        # Act
        response = await search_service.search_notes(user_id, request)

        # Assert
        search_service.note_repo.search_notes.assert_called_once_with(
            user_id=user_id,
            query="meeting",
            tag_filter=["work"]
        )

        assert response.total == 1
        assert len(response.items) == 1
        assert response.items[0].title == "Work Meeting Notes"
        assert len(response.items[0].tags) == 1
        assert "work" in response.items[0].tags

    @pytest.mark.asyncio
    async def test_search_with_multiple_tag_filters(
        self, search_service, user_id, mock_note_with_work_tag
    ):
        """Test search with multiple tag filters."""
        # Arrange
        search_service.note_repo.search_notes.return_value = [mock_note_with_work_tag]

        request = NoteSearchRequest(
            query="meeting",
            tags=["work", "important"],  # Multiple tags
            page=1,
            per_page=20
        )

        # Act
        await search_service.search_notes(user_id, request)

        # Assert
        search_service.note_repo.search_notes.assert_called_once_with(
            user_id=user_id,
            query="meeting",
            tag_filter=["work", "important"]
        )

    @pytest.mark.asyncio
    async def test_search_without_tag_filter_returns_all_matching_notes(
        self, search_service, user_id, mock_note_with_work_tag, mock_note_with_personal_tag
    ):
        """Test search without tag filter returns all text-matching notes."""
        # Arrange
        all_matching_notes = [mock_note_with_work_tag, mock_note_with_personal_tag]
        search_service.note_repo.search_notes.return_value = all_matching_notes

        request = NoteSearchRequest(
            query="note",  # Generic text that matches both
            tags=None,     # No tag filter
            page=1,
            per_page=20
        )

        # Act
        response = await search_service.search_notes(user_id, request)

        # Assert
        search_service.note_repo.search_notes.assert_called_once_with(
            user_id=user_id,
            query="note",
            tag_filter=None
        )

        assert response.total == 2
        assert len(response.items) == 2

    @pytest.mark.asyncio
    async def test_search_with_empty_tag_list_treated_as_no_filter(
        self, search_service, user_id, mock_note_with_work_tag
    ):
        """Test that empty tag list is treated as no filter."""
        # Arrange
        search_service.note_repo.search_notes.return_value = [mock_note_with_work_tag]

        request = NoteSearchRequest(
            query="meeting",
            tags=[],  # Empty tag list
            page=1,
            per_page=20
        )

        # Act
        await search_service.search_notes(user_id, request)

        # Assert
        search_service.note_repo.search_notes.assert_called_once_with(
            user_id=user_id,
            query="meeting",
            tag_filter=[]
        )

    @pytest.mark.asyncio
    async def test_search_with_nonexistent_tag_returns_empty_results(
        self, search_service, user_id
    ):
        """Test search with non-existent tag returns empty results."""
        # Arrange
        search_service.note_repo.search_notes.return_value = []  # No matching notes

        request = NoteSearchRequest(
            query="meeting",
            tags=["nonexistent"],
            page=1,
            per_page=20
        )

        # Act
        response = await search_service.search_notes(user_id, request)

        # Assert
        assert response.total == 0
        assert len(response.items) == 0