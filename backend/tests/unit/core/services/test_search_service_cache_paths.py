"""Unit tests for SearchService cache and path selection behavior."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.notemesh.core.schemas.notes import NoteSearchRequest
from src.notemesh.core.services.search_service import SearchService


class DummyNote:
    def __init__(self, owner_id: uuid.UUID):
        self.id = uuid.uuid4()
        self.title = "Note Title"
        self.content = "Some content for this note"
        self.owner_id = owner_id
        self.tags = ["work", "test"]
        now = datetime.now(timezone.utc)
        self.created_at = now
        self.updated_at = now


@pytest.fixture
def service():
    s = SearchService(None)  # No DB session to avoid user/share repo lookups
    # Replace repos/clients with mocks
    s.note_repo = AsyncMock()
    s.redis_client.get_cached_search = AsyncMock()
    s.redis_client.search_notes = AsyncMock()
    s.redis_client.cache_search_results = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_early_return_no_query_no_tags(service):
    req = NoteSearchRequest(query="   ", tags=[], page=1, per_page=20)

    resp = await service.search_notes(uuid.uuid4(), req)

    assert resp.total == 0
    assert resp.items == []
    assert resp.pages == 0
    assert resp.filters_applied == {"tag_filter": []}


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_response(service):
    user_id = uuid.uuid4()
    req = NoteSearchRequest(query="test", tags=[], page=1, per_page=20)

    # Shape must match NoteSearchResponse fields
    service.redis_client.get_cached_search.return_value = {
        "items": [],
        "total": 0,
        "page": 1,
        "per_page": 20,
        "pages": 0,
        "has_next": False,
        "has_prev": False,
        "query": "test",
        "filters_applied": {"tag_filter": []},
        "search_time_ms": 0.0,
    }

    resp = await service.search_notes(user_id, req)

    assert resp.total == 0
    service.redis_client.search_notes.assert_not_called()
    service.note_repo.search_notes.assert_not_called()


@pytest.mark.asyncio
async def test_redis_results_path_fetches_notes_by_id(service):
    user_id = uuid.uuid4()
    req = NoteSearchRequest(query="redis path", tags=[], page=1, per_page=20)

    service.redis_client.get_cached_search.return_value = None
    service.redis_client.search_notes.return_value = [{"note_id": str(uuid.uuid4())}]

    dummy = DummyNote(owner_id=user_id)
    service.note_repo.get_by_id = AsyncMock(return_value=dummy)

    resp = await service.search_notes(user_id, req)

    service.note_repo.get_by_id.assert_called_once()
    service.note_repo.search_notes.assert_not_called()
    assert resp.total == 1
    assert len(resp.items) == 1


@pytest.mark.asyncio
async def test_db_fallback_when_no_redis_results(service):
    user_id = uuid.uuid4()
    req = NoteSearchRequest(query="db path", tags=["work"], page=1, per_page=20)

    service.redis_client.get_cached_search.return_value = None
    service.redis_client.search_notes.return_value = []

    dummy = DummyNote(owner_id=user_id)
    service.note_repo.search_notes = AsyncMock(return_value=[dummy])

    resp = await service.search_notes(user_id, req)

    service.note_repo.search_notes.assert_called_once()
    assert resp.total == 1
    assert len(resp.items) == 1
    service.redis_client.cache_search_results.assert_awaited()
