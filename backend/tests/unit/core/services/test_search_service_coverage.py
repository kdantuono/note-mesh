"""Tests to increase search service coverage."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.notemesh.core.services.search_service import SearchService
from src.notemesh.core.schemas.notes import NoteSearchRequest


class TestSearchServiceCoverage:
    """Tests to increase coverage of search service."""

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

    @pytest.mark.asyncio
    async def test_index_note(self, search_service):
        """Test index note functionality."""
        note_id = uuid.uuid4()
        mock_note = Mock()
        mock_note.id = note_id

        search_service.note_repo.get_by_id = AsyncMock(return_value=mock_note)

        result = await search_service.index_note(note_id)

        assert result is True
        search_service.note_repo.get_by_id.assert_called_once_with(note_id)

    @pytest.mark.asyncio
    async def test_index_note_not_found(self, search_service):
        """Test index note when note not found."""
        note_id = uuid.uuid4()

        search_service.note_repo.get_by_id = AsyncMock(return_value=None)

        result = await search_service.index_note(note_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_note_from_index(self, search_service):
        """Test remove note from index."""
        note_id = uuid.uuid4()

        result = await search_service.remove_note_from_index(note_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_suggest_tags_empty_query(self, search_service, user_id):
        """Test suggest tags with empty query."""
        result = await search_service.suggest_tags(user_id, "", 10)

        assert result == []

    @pytest.mark.asyncio
    async def test_suggest_tags_with_matches(self, search_service, user_id):
        """Test suggest tags with matching tags."""
        all_tags = ["work", "workshop", "personal", "project"]
        search_service.note_repo.get_user_tags = AsyncMock(return_value=all_tags)

        result = await search_service.suggest_tags(user_id, "wor", 10)

        # Should return tags containing "wor"
        assert "work" in result
        assert "workshop" in result
        assert "personal" not in result

    @pytest.mark.asyncio
    async def test_suggest_tags_sorting(self, search_service, user_id):
        """Test suggest tags sorting (exact match first, then starts with, then contains)."""
        all_tags = ["networking", "work", "homework", "workshop"]
        search_service.note_repo.get_user_tags = AsyncMock(return_value=all_tags)

        result = await search_service.suggest_tags(user_id, "work", 10)

        # "work" (exact match) should come first
        assert result[0] == "work"

    @pytest.mark.asyncio
    async def test_get_search_stats(self, search_service, user_id):
        """Test get search stats."""
        all_tags = ["work", "personal", "meeting"]
        search_service.note_repo.get_user_tags = AsyncMock(return_value=all_tags)
        search_service.note_repo.list_user_notes = AsyncMock(return_value=([], 15))

        result = await search_service.get_search_stats(user_id)

        assert result["total_notes"] == 15
        assert result["total_tags"] == 3
        assert result["most_used_tags"] == ["work", "personal", "meeting"]
        assert result["searchable_content"] is True

    @pytest.mark.asyncio
    async def test_get_note_sharing_info_exception(self, search_service, user_id):
        """Test _get_note_sharing_info with exception."""
        note_id = uuid.uuid4()

        # Create a mock share repo that raises an exception
        mock_share_repo = Mock()
        mock_share_repo.list_shares_given = AsyncMock(side_effect=Exception("DB Error"))

        result = await search_service._get_note_sharing_info(mock_share_repo, note_id, user_id)

        # Should return fallback values on exception
        assert result["is_shared_by_user"] is False
        assert result["share_count"] == 0
        assert result["shared_with"] == []

    @pytest.mark.asyncio
    async def test_get_note_sharing_info_success(self, search_service, user_id):
        """Test _get_note_sharing_info success case."""
        note_id = uuid.uuid4()

        # Create mock shares
        mock_share1 = Mock()
        mock_share1.note_id = note_id
        mock_share1.is_active = True
        mock_share1.shared_with_username = "user1"

        mock_share2 = Mock()
        mock_share2.note_id = note_id
        mock_share2.is_active = True
        mock_share2.shared_with_username = "user2"

        mock_share_repo = Mock()
        mock_share_repo.list_shares_given = AsyncMock(return_value=([mock_share1, mock_share2], 2))

        result = await search_service._get_note_sharing_info(mock_share_repo, note_id, user_id)

        assert result["is_shared_by_user"] is True
        assert result["share_count"] == 2
        assert "user1" in result["shared_with"]
        assert "user2" in result["shared_with"]

    @pytest.mark.asyncio
    async def test_search_notes_with_session_none(self, user_id):
        """Test search notes when session is None."""
        service = SearchService(None)  # No session
        service.note_repo = AsyncMock()

        mock_note = Mock()
        mock_note.id = uuid.uuid4()
        mock_note.title = "Test Note"
        mock_note.content = "Test content"
        mock_note.owner_id = user_id
        mock_note.created_at = datetime.utcnow()
        mock_note.updated_at = datetime.utcnow()
        mock_note.tags = []

        service.note_repo.search_notes = AsyncMock(return_value=[mock_note])

        request = NoteSearchRequest(query="test", page=1, per_page=20)
        result = await service.search_notes(user_id, request)

        assert result.total == 1
        assert len(result.items) == 1
        # When session is None, owner info should be None
        assert result.items[0].owner_username is None