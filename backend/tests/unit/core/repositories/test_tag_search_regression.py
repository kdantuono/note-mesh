"""TDD test for tag search regression - was working before, now broken."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from src.notemesh.core.repositories.note_repository import NoteRepository


class TestTagSearchRegression:
    """Test that tag search works as it did before."""

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
    async def test_tag_search_should_work_like_before(self, note_repository, user_id):
        """REGRESSION TEST: Tag search should work exactly like it did before shared notes feature."""

        # Create mock note with tags
        mock_note = Mock()
        mock_note.id = uuid.uuid4()
        mock_note.title = "Work Meeting Notes"
        mock_note.content = "Meeting about project planning"
        mock_note.owner_id = user_id
        mock_note.created_at = datetime.now(timezone.utc)
        mock_note.updated_at = datetime.now(timezone.utc)

        # Mock tag
        mock_tag = Mock()
        mock_tag.name = "work"
        mock_note.tags = [mock_tag]

        # Mock SQL result
        mock_result = Mock()
        mock_result.scalars.return_value = [mock_note]
        note_repository.session.execute = AsyncMock(return_value=mock_result)

        # ACT: Search with tag filter (this should work!)
        results = await note_repository.search_notes(
            user_id=user_id,
            query="meeting",
            tag_filter=["work"]
        )

        # ASSERT: Should find the note
        assert len(results) == 1
        assert results[0].title == "Work Meeting Notes"

        # Verify session.execute was called (SQL was generated)
        note_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_tag_search_with_empty_filter_should_work(self, note_repository, user_id):
        """REGRESSION TEST: Tag search with empty filter should work like before."""

        mock_note = Mock()
        mock_note.id = uuid.uuid4()
        mock_note.title = "Any Note"
        mock_note.content = "Any content"
        mock_note.owner_id = user_id
        mock_note.created_at = datetime.now(timezone.utc)
        mock_note.updated_at = datetime.now(timezone.utc)
        mock_note.tags = []

        mock_result = Mock()
        mock_result.scalars.return_value = [mock_note]
        note_repository.session.execute = AsyncMock(return_value=mock_result)

        # ACT: Search without tag filter
        results = await note_repository.search_notes(
            user_id=user_id,
            query="content",
            tag_filter=None
        )

        # ASSERT: Should find the note
        assert len(results) == 1
        note_repository.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_sql_generation_should_not_break_with_shares_and_tags(self, note_repository, user_id):
        """Test that adding shares table doesn't break SQL when combined with tag joins."""

        # This test specifically checks that we don't get invalid SQL
        # when combining shared notes access with tag filtering

        mock_result = Mock()
        mock_result.scalars.return_value = []
        note_repository.session.execute = AsyncMock(return_value=mock_result)

        # This should not raise an SQL error
        try:
            await note_repository.search_notes(
                user_id=user_id,
                query="test",
                tag_filter=["work", "important"]
            )
            sql_generation_success = True
        except Exception as e:
            print(f"SQL generation failed: {e}")
            sql_generation_success = False

        assert sql_generation_success, "SQL generation should not fail when combining shares and tags"
        note_repository.session.execute.assert_called_once()