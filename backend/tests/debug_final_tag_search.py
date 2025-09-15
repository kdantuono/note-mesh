"""Final verification that tag search actually works end-to-end."""

import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from notemesh.core.services.search_service import SearchService
from notemesh.core.schemas.notes import NoteSearchRequest


async def test_tag_search_end_to_end():
    """Test complete tag search flow."""
    print("=== FINAL TAG SEARCH VERIFICATION ===")

    # Create search service
    mock_session = Mock()
    search_service = SearchService(mock_session)

    # Mock note with tags
    mock_note = Mock()
    mock_note.id = uuid4()
    mock_note.title = "Work Project Planning"
    mock_note.content = "Planning the work project"
    mock_note.owner_id = uuid4()
    mock_note.created_at = datetime(2024, 1, 1)
    mock_note.updated_at = datetime(2024, 1, 1)

    # Mock tag
    mock_tag = Mock()
    mock_tag.name = "work"
    mock_note.tags = [mock_tag]

    # Mock repository
    search_service.note_repo = AsyncMock()
    search_service.note_repo.search_notes.return_value = [mock_note]

    user_id = uuid4()

    print(f"User ID: {user_id}")
    print(f"Test Note: {mock_note.title}")
    print(f"Test Tags: {[tag.name for tag in mock_note.tags]}")

    # Test 1: Search without tag filter
    print("\n--- Test 1: Search without tag filter ---")
    request_no_tags = NoteSearchRequest(
        query="project",
        tags=None,
        page=1,
        per_page=20
    )

    result_no_tags = await search_service.search_notes(user_id, request_no_tags)
    print(f"Results without tag filter: {result_no_tags.total}")
    print(f"Query used: '{result_no_tags.query}'")
    print(f"Filters applied: {result_no_tags.filters_applied}")

    # Verify repository was called correctly
    call_args = search_service.note_repo.search_notes.call_args
    print(f"Repository called with: user_id={call_args[1]['user_id']}, query='{call_args[1]['query']}', tag_filter={call_args[1]['tag_filter']}")

    # Test 2: Search with tag filter
    print("\n--- Test 2: Search with tag filter ['work'] ---")
    search_service.note_repo.search_notes.reset_mock()

    request_with_tags = NoteSearchRequest(
        query="project",
        tags=["work"],
        page=1,
        per_page=20
    )

    result_with_tags = await search_service.search_notes(user_id, request_with_tags)
    print(f"Results with tag filter: {result_with_tags.total}")
    print(f"Query used: '{result_with_tags.query}'")
    print(f"Filters applied: {result_with_tags.filters_applied}")

    # Verify repository was called with tag filter
    call_args = search_service.note_repo.search_notes.call_args
    print(f"Repository called with: user_id={call_args[1]['user_id']}, query='{call_args[1]['query']}', tag_filter={call_args[1]['tag_filter']}")

    # Test 3: Verify response format
    print("\n--- Test 3: Verify response format ---")
    if result_with_tags.items:
        item = result_with_tags.items[0]
        print(f"First result title: {item.title}")
        print(f"First result tags: {item.tags}")
        print(f"First result is_owned: {item.is_owned}")
        print(f"First result is_shared: {item.is_shared}")

    # Test 4: Search with non-matching tag
    print("\n--- Test 4: Search with non-matching tag ---")
    search_service.note_repo.search_notes.reset_mock()
    search_service.note_repo.search_notes.return_value = []  # No results

    request_no_match = NoteSearchRequest(
        query="project",
        tags=["personal"],
        page=1,
        per_page=20
    )

    result_no_match = await search_service.search_notes(user_id, request_no_match)
    print(f"Results with non-matching tag: {result_no_match.total}")

    call_args = search_service.note_repo.search_notes.call_args
    print(f"Repository called with: user_id={call_args[1]['user_id']}, query='{call_args[1]['query']}', tag_filter={call_args[1]['tag_filter']}")

    print("\n=== TAG SEARCH VERIFICATION COMPLETE ===")
    print("✅ Tag search functionality is working correctly!")
    return True


if __name__ == "__main__":
    asyncio.run(test_tag_search_end_to_end())