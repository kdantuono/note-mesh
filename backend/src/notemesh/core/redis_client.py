"""Redis client for caching and session management."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional, Dict
from uuid import UUID

import redis.asyncio as redis
from pydantic import BaseModel

from ..config import get_settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for caching and session management."""

    def __init__(self):
        self.settings = get_settings()
        self.redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis = redis.from_url(
                self.settings.redis_url,
                max_connections=self.settings.redis_max_connections,
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        if not self.redis:
            return None
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration."""
        if not self.redis:
            return False
        try:
            if expire:
                return await self.redis.setex(key, expire, value)
            else:
                return await self.redis.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self.redis:
            return False
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.redis:
            return False
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    # Cache methods for common operations
    async def cache_search_results(self, query: str, user_id: UUID, results: Dict[str, Any], expire: int = 300) -> bool:
        """Cache search results for 5 minutes by default."""
        cache_key = f"search:{user_id}:{hash(query)}"
        try:
            return await self.set(cache_key, json.dumps(results), expire)
        except Exception as e:
            logger.error(f"Failed to cache search results: {e}")
            return False

    async def get_cached_search(self, query: str, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get cached search results."""
        cache_key = f"search:{user_id}:{hash(query)}"
        try:
            cached = await self.get(cache_key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached search: {e}")
            return None

    async def cache_user_session(self, session_id: str, user_data: Dict[str, Any], expire: int = 3600) -> bool:
        """Cache user session for 1 hour by default."""
        session_key = f"session:{session_id}"
        try:
            return await self.set(session_key, json.dumps(user_data), expire)
        except Exception as e:
            logger.error(f"Failed to cache user session: {e}")
            return False

    async def get_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user session data."""
        session_key = f"session:{session_id}"
        try:
            session_data = await self.get(session_key)
            if session_data:
                return json.loads(session_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get user session: {e}")
            return None

    async def invalidate_user_sessions(self, user_id: UUID) -> bool:
        """Invalidate all sessions for a user (for logout)."""
        try:
            pattern = f"session:*:{user_id}"
            if self.redis:
                keys = await self.redis.keys(pattern)
                if keys:
                    return await self.redis.delete(*keys) > 0
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate user sessions: {e}")
            return False

    async def add_to_blacklist(self, token_jti: str, expire: int = 900) -> bool:
        """Add token to blacklist (for secure logout)."""
        blacklist_key = f"blacklist:{token_jti}"
        try:
            return await self.set(blacklist_key, "blacklisted", expire)
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False

    async def is_token_blacklisted(self, token_jti: str) -> bool:
        """Check if token is blacklisted."""
        blacklist_key = f"blacklist:{token_jti}"
        return await self.exists(blacklist_key)

    # Full-text search methods
    async def index_note_for_search(self, note_id: UUID, title: str, content: str, tags: list[str], user_id: UUID) -> bool:
        """Index note content in Redis for full-text search."""
        try:
            if not self.redis:
                return False

            # Create search document
            search_doc = {
                "id": str(note_id),
                "title": title,
                "content": content,
                "tags": " ".join(tags),
                "user_id": str(user_id),
                "searchable_text": f"{title} {content} {' '.join(tags)}".lower(),
                "indexed_at": str(datetime.now(timezone.utc).isoformat())
            }

            # Store in Redis with key pattern: search:note:{note_id}
            search_key = f"search:note:{note_id}"
            await self.set(search_key, json.dumps(search_doc), expire=86400)  # 24 hours

            # Also store in user's search index for faster user-specific searches
            user_search_key = f"search:user:{user_id}"
            await self.redis.sadd(user_search_key, str(note_id))
            await self.redis.expire(user_search_key, 86400)

            # Store searchable words for full-text capabilities
            words = search_doc["searchable_text"].split()
            for word in words:
                if len(word) > 2:  # Only index words longer than 2 chars
                    word_key = f"search:word:{word}"
                    await self.redis.sadd(word_key, str(note_id))
                    await self.redis.expire(word_key, 86400)

            logger.info(f"Indexed note {note_id} for search with {len(words)} words")
            return True

        except Exception as e:
            logger.error(f"Failed to index note for search: {e}")
            return False

    async def search_notes(self, query: str, user_id: UUID, tags: list[str] = None) -> list[dict]:
        """Search notes via Redis full-text search."""
        try:
            if not self.redis:
                return []

            # Normalize query
            query_words = query.lower().split()
            if not query_words:
                return []

            # Find note IDs that contain any of the search words
            note_ids = set()
            for word in query_words:
                word_key = f"search:word:{word}"
                word_results = await self.redis.smembers(word_key)
                if word_results:
                    note_ids.update(word_results)

            # If no results from word search, return empty
            if not note_ids:
                return []

            # Get user's accessible notes
            user_search_key = f"search:user:{user_id}"
            user_notes = await self.redis.smembers(user_search_key)

            # Intersect with user's accessible notes
            accessible_note_ids = note_ids.intersection(set(user_notes))

            # Retrieve and score the results
            results = []
            for note_id in accessible_note_ids:
                search_key = f"search:note:{note_id}"
                note_data = await self.get(search_key)

                if note_data:
                    note_doc = json.loads(note_data)

                    # Simple scoring based on word matches
                    score = 0
                    searchable_text = note_doc.get("searchable_text", "")

                    for word in query_words:
                        if word in searchable_text:
                            # Higher score for title matches
                            if word in note_doc.get("title", "").lower():
                                score += 2
                            # Normal score for content matches
                            elif word in note_doc.get("content", "").lower():
                                score += 1
                            # Bonus for exact tag matches
                            elif word in note_doc.get("tags", "").lower():
                                score += 3

                    # Apply tag filter if provided
                    if tags:
                        note_tags = note_doc.get("tags", "").split()
                        if not any(tag.lower() in [t.lower() for t in note_tags] for tag in tags):
                            continue  # Skip if doesn't match tag filter

                    results.append({
                        "note_id": note_id,
                        "score": score,
                        "title": note_doc.get("title", ""),
                        "content_preview": note_doc.get("content", "")[:200] + "..." if len(note_doc.get("content", "")) > 200 else note_doc.get("content", "")
                    })

            # Sort by score (highest first)
            results.sort(key=lambda x: x["score"], reverse=True)

            logger.info(f"Redis search for '{query}' found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Redis search failed: {e}")
            return []

    async def search_notes_with_tags(self, query: str, tags: list[str], user_id: UUID) -> list[dict]:
        """Search notes with tag filter via Redis."""
        return await self.search_notes(query, user_id, tags)

    async def remove_note_from_search(self, note_id: UUID) -> bool:
        """Remove note from Redis search index."""
        try:
            if not self.redis:
                return False

            # Get the note document first to remove from word indices
            search_key = f"search:note:{note_id}"
            note_data = await self.get(search_key)

            if note_data:
                note_doc = json.loads(note_data)

                # Remove from word indices
                words = note_doc.get("searchable_text", "").split()
                for word in words:
                    if len(word) > 2:
                        word_key = f"search:word:{word}"
                        await self.redis.srem(word_key, str(note_id))

                # Remove from user index
                user_id = note_doc.get("user_id")
                if user_id:
                    user_search_key = f"search:user:{user_id}"
                    await self.redis.srem(user_search_key, str(note_id))

            # Remove the note document
            await self.delete(search_key)

            logger.info(f"Removed note {note_id} from search index")
            return True

        except Exception as e:
            logger.error(f"Failed to remove note from search index: {e}")
            return False

    # Rate limiting
    async def increment_rate_limit(self, key: str, expire: int = 60) -> int:
        """Increment rate limit counter."""
        try:
            if not self.redis:
                return 0
            # Use pipeline for atomic operation
            async with self.redis.pipeline() as pipe:
                await pipe.incr(key)
                await pipe.expire(key, expire)
                results = await pipe.execute()
                return results[0] if results else 0
        except Exception as e:
            logger.error(f"Rate limit error for key {key}: {e}")
            return 0

    async def get_rate_limit(self, key: str) -> int:
        """Get current rate limit count."""
        try:
            if not self.redis:
                return 0
            count = await self.redis.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Get rate limit error for key {key}: {e}")
            return 0


# Singleton instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client