"""Search service implementation."""

import json
import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.note_repository import NoteRepository
from ..schemas.notes import NoteSearchRequest, NoteSearchResponse
from ..redis_client import get_redis_client
from .interfaces import ISearchService

logger = logging.getLogger(__name__)


class SearchService(ISearchService):
    """Search service implementation."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.note_repo = NoteRepository(session)
        self.redis_client = get_redis_client()

    async def search_notes(self, user_id: UUID, request: NoteSearchRequest) -> NoteSearchResponse:
        """Search notes with filters - with Redis caching."""
        import time
        start_time = time.time()

        # Allow search with only tag filter (no query text)
        has_query = request.query.strip() and request.query.strip() != "*"
        has_tags = request.tags and len(request.tags) > 0

        if not has_query and not has_tags:
            # If no query and no tags, return empty results
            return NoteSearchResponse(
                items=[],
                total=0,
                page=request.page or 1,
                per_page=request.per_page or 20,
                pages=0,
                has_next=False,
                has_prev=False,
                query=request.query,
                filters_applied={"tag_filter": request.tags or []},
                search_time_ms=0.0,
            )

        # Create cache key from search parameters
        cache_key_data = {
            "query": request.query.strip(),
            "tags": sorted(request.tags) if request.tags else [],
            "page": request.page or 1,
            "per_page": request.per_page or 20,
        }
        cache_key = f"search:{user_id}:{hash(str(cache_key_data))}"

        # Try to get cached results first
        try:
            cached_result = await self.redis_client.get_cached_search(
                str(cache_key_data), user_id
            )
            if cached_result:
                logger.info(f"Cache HIT for search query: {request.query}")
                # Convert back to NoteSearchResponse
                search_time_ms = (time.time() - start_time) * 1000
                cached_result["search_time_ms"] = search_time_ms
                cached_result["cached"] = True
                return NoteSearchResponse(**cached_result)
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")

        logger.info(f"Cache MISS for search query: {request.query}")

        # Try Redis full-text search FIRST (if available)
        redis_results = []
        try:
            redis_results = await self.redis_client.search_notes(
                query=request.query.strip(),
                user_id=user_id,
                tags=request.tags or []
            )
            logger.info(f"Redis full-text search returned {len(redis_results)} results")
        except Exception as e:
            logger.warning(f"Redis search failed, falling back to database: {e}")

        # If Redis search found results, use them; otherwise fallback to database
        if redis_results:
            logger.info(f"Using Redis search results for query: {request.query}")
            # Convert Redis results to notes
            notes = []
            for result in redis_results:
                # We need to fetch the actual note objects from database
                # using the note IDs from Redis results
                try:
                    note_id = UUID(result["note_id"])
                    note = await self.note_repo.get_by_id(note_id)
                    if note:
                        notes.append(note)
                except Exception as e:
                    logger.warning(f"Failed to fetch note {result.get('note_id')}: {e}")
        else:
            logger.info(f"Using database search for query: {request.query}")
            # Fallback to database search
            notes = await self.note_repo.search_notes(
                user_id=user_id, query=request.query.strip(), tag_filter=request.tags
            )

        # Convert to list item format for search results
        from ..schemas.notes import NoteListItem

        note_list_items = []

        # Get repositories if session is available
        user_repo = None
        share_repo = None
        if self.session is not None:
            from ..repositories.user_repository import UserRepository
            from ..repositories.share_repository import ShareRepository
            user_repo = UserRepository(self.session)
            share_repo = ShareRepository(self.session)

        for note in notes:
            # Get owner information if user repository is available
            owner_username = None
            owner_display_name = None
            if user_repo:
                try:
                    owner_info = await user_repo.get_by_id(note.owner_id)
                    owner_username = owner_info.username if owner_info else None
                    owner_display_name = owner_info.full_name if owner_info else None
                except Exception:
                    # Fallback if user lookup fails
                    pass

            # Create content preview
            content_preview = note.content[:200] + "..." if len(note.content) > 200 else note.content

            # Get sharing information if share repository is available
            is_shared_by_user = False
            share_count = 0
            if share_repo:
                try:
                    sharing_info = await self._get_note_sharing_info(share_repo, note.id, user_id)
                    is_shared_by_user = sharing_info.get("is_shared_by_user", False)
                    share_count = sharing_info.get("share_count", 0)
                except Exception:
                    # Fallback if sharing lookup fails
                    pass

            # Determine ownership: is this note owned by the current user?
            is_owned = note.owner_id == user_id
            is_shared = not is_owned  # If not owned, then it's shared with user
            can_edit = is_owned  # Only owners can edit (default read-only for shared)

            note_list_item = NoteListItem(
                id=note.id,
                title=note.title,
                content_preview=content_preview,
                tags=[tag.name if hasattr(tag, 'name') else str(tag) for tag in getattr(note, 'tags', [])],
                owner_id=note.owner_id,
                owner_username=owner_username,
                owner_display_name=owner_display_name,
                is_shared=is_shared,  # True if shared with user, False if owned
                is_owned=is_owned,    # True if owned by user, False if shared
                can_edit=can_edit,    # True if owned, False if shared (read-only)
                is_shared_by_user=is_shared_by_user,
                share_count=share_count,
                created_at=note.created_at,
                updated_at=note.updated_at
            )
            note_list_items.append(note_list_item)

        # Apply pagination
        page = request.page or 1
        per_page = request.per_page or 20
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        paginated_notes = note_list_items[start_idx:end_idx]

        # Calculate search time
        search_time_ms = (time.time() - start_time) * 1000

        # Build response
        response = NoteSearchResponse(
            items=paginated_notes,
            total=len(note_list_items),
            page=page,
            per_page=per_page,
            pages=(len(note_list_items) + per_page - 1) // per_page,
            has_next=end_idx < len(note_list_items),
            has_prev=page > 1,
            query=request.query,
            filters_applied={"tag_filter": request.tags or []},
            search_time_ms=search_time_ms,
        )

        # Cache the results for 5 minutes (300 seconds)
        try:
            response_dict = response.dict()
            await self.redis_client.cache_search_results(
                str(cache_key_data), user_id, response_dict, expire=300
            )
            logger.info(f"Cached search results for query: {request.query}")
        except Exception as e:
            logger.warning(f"Failed to cache search results: {e}")

        return response

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

    async def _get_note_sharing_info(self, share_repo, note_id: UUID, user_id: UUID) -> dict:
        """Get sharing information for a note owned by the user."""
        try:
            # Count active shares for this note created by the user
            shares_given, _ = await share_repo.list_shares_given(user_id, page=1, per_page=1000)
            note_shares = [share for share in shares_given if share.note_id == note_id and getattr(share, 'is_active', True)]

            return {
                "is_shared_by_user": len(note_shares) > 0,
                "share_count": len(note_shares),
                "shared_with": [getattr(share, 'shared_with_username', 'Unknown') for share in note_shares]
            }
        except Exception:
            # Fallback in case of any error
            return {
                "is_shared_by_user": False,
                "share_count": 0,
                "shared_with": []
            }

    async def suggest_tags(self, user_id: UUID, query: str, limit: int = 10) -> List[str]:
        """Suggest tags based on query - with Redis caching."""
        if not query.strip():
            return []

        # Create cache key for tag suggestions
        cache_key = f"tag_suggestions:{user_id}:{query.lower()}:{limit}"

        # Try to get cached results first
        try:
            cached_result = await self.redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Cache HIT for tag suggestions: {query}")
                import json
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"Tag suggestions cache lookup failed: {e}")

        logger.info(f"Cache MISS for tag suggestions: {query}")

        # Get all user tags from database
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
        result = matching_tags[:limit]

        # Cache the results for 5 minutes (300 seconds)
        try:
            import json
            await self.redis_client.set(cache_key, json.dumps(result), expire=300)
            logger.info(f"Cached tag suggestions for query: {query}")
        except Exception as e:
            logger.warning(f"Failed to cache tag suggestions: {e}")

        return result

    async def get_search_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get user search stats - with Redis caching."""
        # Create cache key for search stats
        cache_key = f"search_stats:{user_id}"

        # Try to get cached results first
        try:
            cached_result = await self.redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Cache HIT for search stats: {user_id}")
                import json
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"Search stats cache lookup failed: {e}")

        logger.info(f"Cache MISS for search stats: {user_id}")

        # Get basic stats about user's notes from database
        all_tags = await self.note_repo.get_user_tags(user_id)

        # Count notes (using a simple approach)
        notes, total_count = await self.note_repo.list_user_notes(user_id, page=1, per_page=1)

        result = {
            "total_notes": total_count,
            "total_tags": len(all_tags),
            "most_used_tags": all_tags[:10],  # Top 10 tags (could be improved with usage count)
            "searchable_content": True,
        }

        # Cache the results for 10 minutes (600 seconds) since stats change less frequently
        try:
            import json
            await self.redis_client.set(cache_key, json.dumps(result), expire=600)
            logger.info(f"Cached search stats for user: {user_id}")
        except Exception as e:
            logger.warning(f"Failed to cache search stats: {e}")

        return result
