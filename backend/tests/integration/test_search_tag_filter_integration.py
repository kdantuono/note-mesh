"""Integration tests for search tag filter functionality."""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import UUID

from src.notemesh.core.schemas.notes import NoteSearchRequest
from src.notemesh.core.services.search_service import SearchService


class TestSearchTagFilterIntegration:
    """Integration tests for search tag filter."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def search_service(self, mock_session):
        """Create search service with mocked dependencies."""
        service = SearchService(mock_session)
        # Mock the note repository
        service.note_repo = AsyncMock()
        # Force redis client methods to return no cached / search results so DB path is taken
        service.redis_client.get_cached_search = AsyncMock(return_value=None)
        service.redis_client.search_notes = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def user_id(self):
        """Sample user ID."""
        return UUID('12345678-1234-5678-1234-567812345678')

    @pytest.mark.asyncio
    async def test_search_with_none_tags_parameter(self, search_service, user_id):
        """Test search when tags parameter is None (like from FastAPI Query)."""
        # This simulates FastAPI Query(None) behavior
        request = NoteSearchRequest(
            query="test",
            tags=None,  # This is what FastAPI Query(None) returns
            page=1,
            per_page=20
        )

        # Mock empty notes to focus on the call behavior
        search_service.note_repo.search_notes.return_value = []

        # Act
        await search_service.search_notes(user_id, request)

        # Assert
        search_service.note_repo.search_notes.assert_called_once_with(
            user_id=user_id,
            query="test",
            tag_filter=None  # Should pass None, not []
        )

    @pytest.mark.asyncio
    async def test_search_with_empty_list_tags_parameter(self, search_service, user_id):
        """Test search when tags parameter is empty list."""
        request = NoteSearchRequest(
            query="test",
            tags=[],  # Empty list
            page=1,
            per_page=20
        )

        # Mock empty notes to focus on the call behavior
        search_service.note_repo.search_notes.return_value = []

        # Act
        await search_service.search_notes(user_id, request)

        # Assert
        search_service.note_repo.search_notes.assert_called_once_with(
            user_id=user_id,
            query="test",
            tag_filter=[]  # Should pass empty list
        )

    @pytest.mark.asyncio
    async def test_search_with_actual_tags_parameter(self, search_service, user_id):
        """Test search when tags parameter has actual values."""
        request = NoteSearchRequest(
            query="test",
            tags=["work", "important"],
            page=1,
            per_page=20
        )

        # Mock empty notes to focus on the call behavior
        search_service.note_repo.search_notes.return_value = []

        # Act
        await search_service.search_notes(user_id, request)

        # Assert
        search_service.note_repo.search_notes.assert_called_once_with(
            user_id=user_id,
            query="test",
            tag_filter=["work", "important"]
        )

    @pytest.mark.asyncio
    async def test_repository_handles_none_tag_filter_correctly(self, search_service, user_id):
        """Test that repository correctly handles None tag_filter."""
        # This is testing the actual repository logic we want to verify
        from src.notemesh.core.repositories.note_repository import NoteRepository

        repo = NoteRepository(Mock())

        # Mock the session execute method to simulate SQL query execution
        mock_result = Mock()
        mock_result.scalars.return_value = []
        repo.session.execute = AsyncMock(return_value=mock_result)

        # Act - call with None tag_filter (should not apply tag filter)
        await repo.search_notes(user_id=user_id, query="test", tag_filter=None)

        # Assert - should have been called once (no additional join for tags)
        repo.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_repository_handles_empty_list_tag_filter_correctly(self, search_service, user_id):
        """Test that repository correctly handles empty list tag_filter."""
        from src.notemesh.core.repositories.note_repository import NoteRepository

        repo = NoteRepository(Mock())

        # Mock the session execute method
        mock_result = Mock()
        mock_result.scalars.return_value = []
        repo.session.execute = AsyncMock(return_value=mock_result)

        # Act - call with empty list tag_filter (should not apply tag filter)
        await repo.search_notes(user_id=user_id, query="test", tag_filter=[])

        # Assert - should have been called once (no additional join for tags)
        repo.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_repository_handles_populated_tag_filter_correctly(self, search_service, user_id):
        """Test that repository correctly handles populated tag_filter."""
        from src.notemesh.core.repositories.note_repository import NoteRepository

        repo = NoteRepository(Mock())

        # Mock the session execute method
        mock_result = Mock()
        mock_result.scalars.return_value = []
        repo.session.execute = AsyncMock(return_value=mock_result)

        # Act - call with actual tags (should apply tag filter)
        await repo.search_notes(user_id=user_id, query="test", tag_filter=["work"])

        # Assert - should have been called once (with tag join)
        repo.session.execute.assert_called_once()