"""Search service implementation."""

from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.note_repository import NoteRepository
from ..schemas.notes import NoteSearchRequest, NoteSearchResponse
from .interfaces import ISearchService


class SearchService(ISearchService):
    """Search service implementation."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.note_repo = NoteRepository(session)

    async def search_notes(self, user_id: UUID, request: NoteSearchRequest) -> NoteSearchResponse:
        """Search notes with filters."""
        if not request.query.strip():
            # If empty query, return empty results
            return NoteSearchResponse(
                notes=[],
                total_count=0,
                query=request.query,
                page=request.page or 1,
                per_page=request.per_page or 20,
            )

        # Use repository search
        notes = await self.note_repo.search_notes(
            user_id=user_id, query=request.query.strip(), tag_filter=request.tags
        )

        # Convert to list item format for search results
        from .note_service import NoteService

        note_service = NoteService(self.session)
        note_list_items = []
        for note in notes:
            note_list_item = note_service._note_to_list_item(note, user_id)
            note_list_items.append(note_list_item)

        # Apply pagination
        page = request.page or 1
        per_page = request.per_page or 20
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        paginated_notes = note_list_items[start_idx:end_idx]

        return NoteSearchResponse(
            items=paginated_notes,
            total=len(note_list_items),
            page=page,
            per_page=per_page,
            pages=(len(note_list_items) + per_page - 1) // per_page,
            has_next=end_idx < len(note_list_items),
            has_prev=page > 1,
            query=request.query,
            filters_applied={"tag_filter": request.tags or []},
            search_time_ms=None,  # Could be implemented with timing
        )

    async def index_note(self, note_id: UUID) -> bool:
        """Index note for search."""
        # For basic implementation, we rely on database full-text search
        # In a real application, this would index in Elasticsearch or similar
        note = await self.note_repo.get_by_id(note_id)
        return note is not None

    async def remove_note_from_index(self, note_id: UUID) -> bool:
        """Remove note from search index."""
        # For basic implementation, deletion from DB handles this
        # In a real application, this would remove from search index
        return True

    async def suggest_tags(self, user_id: UUID, query: str, limit: int = 10) -> List[str]:
        """Suggest tags based on query."""
        if not query.strip():
            return []

        # Get all user tags
        all_tags = await self.note_repo.get_user_tags(user_id)

        # Filter tags that contain the query (case insensitive)
        query_lower = query.lower()
        matching_tags = [tag for tag in all_tags if query_lower in tag.lower()]

        # Sort by relevance (exact match first, then starts with, then contains)
        def tag_score(tag: str) -> int:
            tag_lower = tag.lower()
            if tag_lower == query_lower:
                return 0  # Exact match
            elif tag_lower.startswith(query_lower):
                return 1  # Starts with query
            else:
                return 2  # Contains query

        matching_tags.sort(key=lambda t: (tag_score(t), len(t), t))

        return matching_tags[:limit]

    async def get_search_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get user search stats."""
        # Get basic stats about user's notes
        all_tags = await self.note_repo.get_user_tags(user_id)

        # Count notes (using a simple approach)
        notes, total_count = await self.note_repo.list_user_notes(user_id, page=1, per_page=1)

        return {
            "total_notes": total_count,
            "total_tags": len(all_tags),
            "most_used_tags": all_tags[:10],  # Top 10 tags (could be improved with usage count)
            "searchable_content": True,
        }
