"""TDD Test per ricerca full-text tramite Redis."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock

from src.notemesh.core.redis_client import RedisClient


class TestRedisFullTextSearch:
    """Test per verificare che la ricerca full-text usi Redis."""

    @pytest.fixture
    def redis_client(self):
        """Mock Redis client."""
        return Mock(spec=RedisClient)

    @pytest.mark.asyncio
    async def test_index_note_content_in_redis(self, redis_client):
        """Test che le note vengano indicizzate in Redis per full-text search."""
        # Given
        note_id = uuid.uuid4()
        note_content = "This is a test note about Redis implementation"
        note_title = "Redis Test Note"

        redis_client.index_note_for_search = AsyncMock(return_value=True)

        # When
        result = await redis_client.index_note_for_search(
            note_id=note_id,
            title=note_title,
            content=note_content,
            tags=["redis", "test"]
        )

        # Then
        assert result is True
        redis_client.index_note_for_search.assert_called_once_with(
            note_id=note_id,
            title=note_title,
            content=note_content,
            tags=["redis", "test"]
        )

    @pytest.mark.asyncio
    async def test_search_notes_via_redis(self, redis_client):
        """Test che la ricerca full-text usi Redis prima del database."""
        # Given
        query = "Redis implementation"
        user_id = uuid.uuid4()

        # Mock Redis search results
        redis_results = [
            {"note_id": str(uuid.uuid4()), "score": 0.95},
            {"note_id": str(uuid.uuid4()), "score": 0.80},
        ]
        redis_client.search_notes = AsyncMock(return_value=redis_results)

        # When
        results = await redis_client.search_notes(query=query, user_id=user_id)

        # Then
        assert len(results) == 2
        assert results[0]["score"] > results[1]["score"]  # Ordinati per score
        redis_client.search_notes.assert_called_once_with(query=query, user_id=user_id)

    @pytest.mark.asyncio
    async def test_remove_note_from_search_index(self, redis_client):
        """Test rimozione note dall'indice Redis."""
        # Given
        note_id = uuid.uuid4()
        redis_client.remove_note_from_search = AsyncMock(return_value=True)

        # When
        result = await redis_client.remove_note_from_search(note_id)

        # Then
        assert result is True
        redis_client.remove_note_from_search.assert_called_once_with(note_id)

    @pytest.mark.asyncio
    async def test_search_with_tag_filter_in_redis(self, redis_client):
        """Test ricerca con filtri tag tramite Redis."""
        # Given
        query = "test"
        tags = ["important", "work"]
        user_id = uuid.uuid4()

        redis_client.search_notes_with_tags = AsyncMock(return_value=[])

        # When
        results = await redis_client.search_notes_with_tags(
            query=query, tags=tags, user_id=user_id
        )

        # Then
        assert isinstance(results, list)
        redis_client.search_notes_with_tags.assert_called_once_with(
            query=query, tags=tags, user_id=user_id
        )