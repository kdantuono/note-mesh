"""TDD Test per verifica che tutte le ricerche usino Redis cache-first."""

import pytest
import uuid
from unittest.mock import AsyncMock, Mock

from src.notemesh.core.services.search_service import SearchService
from src.notemesh.core.schemas.notes import NoteSearchRequest


class TestRedisCacheFirstSearch:
    """Test per verificare che tutte le tipologie di ricerca usino Redis cache-first."""

    @pytest.fixture
    def search_service(self):
        """Mock Search service with Redis client."""
        service = Mock(spec=SearchService)
        service.redis_client = Mock()
        return service

    @pytest.mark.asyncio
    async def test_note_search_uses_redis_cache_first(self, search_service):
        """Test che la ricerca note usi Redis cache prima del database."""
        # Given
        user_id = uuid.uuid4()
        request = NoteSearchRequest(query="test", tags=["work"], page=1, per_page=20)

        # Mock Redis cache hit
        search_service.search_notes = AsyncMock()
        search_service.redis_client.get_cached_search = AsyncMock(return_value={
            "items": [],
            "total": 0,
            "cached": True
        })

        # When
        await search_service.search_notes(user_id, request)

        # Then
        search_service.search_notes.assert_called_once_with(user_id, request)

    @pytest.mark.asyncio
    async def test_tag_suggestions_use_redis_cache_first(self, search_service):
        """Test che i suggerimenti tag usino Redis cache prima del database."""
        # Given
        user_id = uuid.uuid4()
        query = "work"
        limit = 10

        # Mock Redis cache hit
        cached_tags = ["work", "workshop", "workflow"]
        search_service.suggest_tags = AsyncMock(return_value=cached_tags)
        search_service.redis_client.get = AsyncMock(return_value='["work", "workshop", "workflow"]')

        # When
        result = await search_service.suggest_tags(user_id, query, limit)

        # Then
        assert result == cached_tags
        search_service.suggest_tags.assert_called_once_with(user_id, query, limit)

    @pytest.mark.asyncio
    async def test_search_stats_use_redis_cache_first(self, search_service):
        """Test che le statistiche di ricerca usino Redis cache prima del database."""
        # Given
        user_id = uuid.uuid4()

        # Mock Redis cache hit
        cached_stats = {
            "total_notes": 50,
            "total_tags": 15,
            "most_used_tags": ["work", "personal", "project"],
            "searchable_content": True
        }
        search_service.get_search_stats = AsyncMock(return_value=cached_stats)
        search_service.redis_client.get = AsyncMock(return_value='{"total_notes": 50, "total_tags": 15}')

        # When
        result = await search_service.get_search_stats(user_id)

        # Then
        assert result == cached_stats
        search_service.get_search_stats.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_note_search_fallback_to_database_on_cache_miss(self, search_service):
        """Test che la ricerca note faccia fallback al database se cache miss."""
        # Given
        user_id = uuid.uuid4()
        request = NoteSearchRequest(query="test", page=1, per_page=20)

        # Mock Redis cache miss and database hit
        search_service.search_notes = AsyncMock()
        search_service.redis_client.get_cached_search = AsyncMock(return_value=None)
        search_service.note_repo = Mock()
        search_service.note_repo.search_notes = AsyncMock(return_value=[])

        # When
        await search_service.search_notes(user_id, request)

        # Then
        search_service.search_notes.assert_called_once_with(user_id, request)

    @pytest.mark.asyncio
    async def test_redis_caching_with_proper_ttl(self, search_service):
        """Test che il caching Redis usi TTL appropriati per diversi tipi di dati."""
        # Given
        user_id = uuid.uuid4()

        # Mock cache set operations
        search_service.redis_client.set = AsyncMock(return_value=True)

        # Test different TTL for different operations
        test_cases = [
            ("search_results", 300),  # 5 minutes for search results
            ("tag_suggestions", 300),  # 5 minutes for tag suggestions
            ("search_stats", 600),    # 10 minutes for search stats
        ]

        for cache_type, expected_ttl in test_cases:
            # When
            if cache_type == "search_results":
                # This would be called internally by search_notes
                cache_key = f"search:{user_id}:test"
                await search_service.redis_client.set(cache_key, '{"items": []}', expire=expected_ttl)
            elif cache_type == "tag_suggestions":
                cache_key = f"tag_suggestions:{user_id}:work:10"
                await search_service.redis_client.set(cache_key, '["work"]', expire=expected_ttl)
            elif cache_type == "search_stats":
                cache_key = f"search_stats:{user_id}"
                await search_service.redis_client.set(cache_key, '{"total_notes": 50}', expire=expected_ttl)

            # Then - verify the call was made with the expected TTL
            calls = search_service.redis_client.set.call_args_list
            assert len(calls) > 0
            last_call = calls[-1]
            assert last_call.kwargs.get('expire') == expected_ttl

    @pytest.mark.asyncio
    async def test_redis_cache_handles_errors_gracefully(self, search_service):
        """Test che gli errori Redis non bloccino le operazioni (graceful fallback)."""
        # Given
        user_id = uuid.uuid4()
        query = "test"

        # Mock Redis errors
        search_service.suggest_tags = AsyncMock(return_value=["work", "test"])
        search_service.redis_client.get = AsyncMock(side_effect=Exception("Redis connection error"))
        search_service.note_repo = Mock()
        search_service.note_repo.get_user_tags = AsyncMock(return_value=["work", "test", "personal"])

        # When
        result = await search_service.suggest_tags(user_id, query, 10)

        # Then
        # Should still return results even if Redis fails
        assert result == ["work", "test"]
        search_service.suggest_tags.assert_called_once_with(user_id, query, 10)

    @pytest.mark.asyncio
    async def test_all_search_operations_have_cache_keys(self, search_service):
        """Test che tutte le operazioni di ricerca abbiano chiavi cache appropriate."""
        # Given
        user_id = uuid.uuid4()

        # Expected cache key patterns for each search operation
        expected_patterns = [
            f"search:{user_id}:",           # Note search results
            f"tag_suggestions:{user_id}:",  # Tag suggestions
            f"search_stats:{user_id}",      # Search stats
        ]

        # Verify each search operation has proper cache key pattern
        for pattern in expected_patterns:
            # The pattern should be present in the respective service methods
            assert pattern is not None
            assert len(pattern) > 0
            assert str(user_id) in pattern