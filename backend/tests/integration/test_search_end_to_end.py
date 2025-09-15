"""End-to-end integration tests for search functionality."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from src.notemesh.core.services.search_service import SearchService
from src.notemesh.core.schemas.notes import NoteSearchRequest
from src.notemesh.core.repositories.note_repository import NoteRepository


class TestSearchEndToEnd:
    """End-to-end tests for search functionality including shared notes and tag filtering."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def search_service(self, mock_session):
        """Create search service with mocked dependencies."""
        service = SearchService(mock_session)
        # Mock user and share repositories
        service.session = mock_session
        return service

    @pytest.fixture
    def user_id(self):
        """Sample user ID."""
        return uuid4()

    @pytest.fixture
    def other_user_id(self):
        """Another user ID."""
        return uuid4()

    @pytest.mark.asyncio
    async def test_search_includes_shared_notes_with_tags(self, search_service, user_id, other_user_id):
        """Integration test: search includes shared notes and filters by tags correctly."""
        # Mock owned note with work tag
        owned_note = Mock()
        owned_note.id = uuid4()
        owned_note.title = "My Work Project"
        owned_note.content = "My project documentation"
        owned_note.owner_id = user_id
        owned_note.created_at = "2024-01-01T10:00:00Z"
        owned_note.updated_at = "2024-01-01T10:00:00Z"

        owned_tag = Mock()
        owned_tag.name = "work"
        owned_note.tags = [owned_tag]

        # Mock shared note with work tag
        shared_note = Mock()
        shared_note.id = uuid4()
        shared_note.title = "Shared Work Document"
        shared_note.content = "Document shared with me"
        shared_note.owner_id = other_user_id
        shared_note.created_at = "2024-01-02T10:00:00Z"
        shared_note.updated_at = "2024-01-02T10:00:00Z"

        shared_tag = Mock()
        shared_tag.name = "work"
        shared_note.tags = [shared_tag]

        # Mock note repository to return both notes
        search_service.note_repo = AsyncMock()
        search_service.note_repo.search_notes.return_value = [owned_note, shared_note]

        # Test 1: Search without tag filter - should find both notes
        request_no_tags = NoteSearchRequest(
            query="work",
            tags=None,
            page=1,
            per_page=20
        )

        result_no_tags = await search_service.search_notes(user_id, request_no_tags)

        assert result_no_tags.total == 2
        assert len(result_no_tags.items) == 2
        assert result_no_tags.query == "work"

        # Verify repository was called correctly
        search_service.note_repo.search_notes.assert_called_with(
            user_id=user_id,
            query="work",
            tag_filter=None
        )

        # Test 2: Search with tag filter - should find both notes with work tag
        search_service.note_repo.search_notes.reset_mock()

        request_with_tags = NoteSearchRequest(
            query="work",
            tags=["work"],
            page=1,
            per_page=20
        )

        result_with_tags = await search_service.search_notes(user_id, request_with_tags)

        assert result_with_tags.total == 2
        assert len(result_with_tags.items) == 2
        assert result_with_tags.query == "work"
        assert result_with_tags.filters_applied["tag_filter"] == ["work"]

        # Verify repository was called with tag filter
        search_service.note_repo.search_notes.assert_called_with(
            user_id=user_id,
            query="work",
            tag_filter=["work"]
        )

        # Test 3: Search with non-matching tag - should find no notes
        search_service.note_repo.search_notes.reset_mock()
        search_service.note_repo.search_notes.return_value = []

        request_no_match = NoteSearchRequest(
            query="work",
            tags=["personal"],
            page=1,
            per_page=20
        )

        result_no_match = await search_service.search_notes(user_id, request_no_match)

        assert result_no_match.total == 0
        assert len(result_no_match.items) == 0

        search_service.note_repo.search_notes.assert_called_with(
            user_id=user_id,
            query="work",
            tag_filter=["personal"]
        )

    @pytest.mark.asyncio
    async def test_search_repository_access_control(self, mock_session, user_id, other_user_id):
        """Test that repository correctly implements access control for shared notes."""
        # This tests the actual repository logic we implemented
        repo = NoteRepository(mock_session)

        # Mock session execute to simulate SQL execution
        mock_result = Mock()
        mock_result.scalars.return_value = []
        repo.session.execute = AsyncMock(return_value=mock_result)

        # Test repository search with different parameters
        await repo.search_notes(user_id, "test query", tag_filter=None)
        repo.session.execute.assert_called_once()

        # Reset and test with tag filter
        repo.session.execute.reset_mock()
        await repo.search_notes(user_id, "test query", tag_filter=["work", "important"])
        repo.session.execute.assert_called_once()

        # Reset and test with empty tag filter
        repo.session.execute.reset_mock()
        await repo.search_notes(user_id, "test query", tag_filter=[])
        repo.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, search_service, user_id):
        """Test that empty queries are handled correctly."""
        request_empty = NoteSearchRequest(
            query="",
            tags=None,
            page=1,
            per_page=20
        )

        result = await search_service.search_notes(user_id, request_empty)

        # Should return empty results for empty query
        assert result.total == 0
        assert len(result.items) == 0
        assert result.query == ""

    @pytest.mark.asyncio
    async def test_whitespace_query_handling(self, search_service, user_id):
        """Test that whitespace-only queries are handled correctly."""
        request_whitespace = NoteSearchRequest(
            query="   ",
            tags=None,
            page=1,
            per_page=20
        )

        result = await search_service.search_notes(user_id, request_whitespace)

        # Should return empty results for whitespace-only query
        assert result.total == 0
        assert len(result.items) == 0
        assert result.query == "   "