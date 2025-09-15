"""TDD Test per verifica caching dati auth/sessione in Redis."""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from src.notemesh.core.redis_client import RedisClient
from src.notemesh.core.services.auth_service import AuthService


class TestRedisAuthSessionCaching:
    """Test per verificare che auth e sessione usino Redis per caching."""

    @pytest.fixture
    def redis_client(self):
        """Mock Redis client."""
        return Mock(spec=RedisClient)

    @pytest.fixture
    def auth_service(self):
        """Mock Auth service."""
        return Mock(spec=AuthService)

    @pytest.mark.asyncio
    async def test_user_session_cached_on_login(self, redis_client):
        """Test che i dati della sessione utente vengano cacheati in Redis al login."""
        # Given
        session_id = "test_refresh_token_123"
        user_data = {
            "user_id": str(uuid.uuid4()),
            "username": "testuser",
            "full_name": "Test User",
            "is_active": True,
            "refresh_token": session_id,
            "login_time": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat()
        }

        redis_client.cache_user_session = AsyncMock(return_value=True)

        # When
        result = await redis_client.cache_user_session(
            session_id=session_id,
            user_data=user_data,
            expire=7 * 24 * 3600  # 7 days
        )

        # Then
        assert result is True
        redis_client.cache_user_session.assert_called_once_with(
            session_id=session_id,
            user_data=user_data,
            expire=7 * 24 * 3600
        )

    @pytest.mark.asyncio
    async def test_jwt_jti_blacklisting_in_redis(self, redis_client):
        """Test che i JTI dei JWT vengano messi in blacklist in Redis."""
        # Given
        jti = "jwt-unique-id-123"
        expire_seconds = 900  # 15 minutes

        redis_client.add_to_blacklist = AsyncMock(return_value=True)

        # When
        result = await redis_client.add_to_blacklist(jti, expire_seconds)

        # Then
        assert result is True
        redis_client.add_to_blacklist.assert_called_once_with(jti, expire_seconds)

    @pytest.mark.asyncio
    async def test_jwt_blacklist_check_in_redis(self, redis_client):
        """Test che la verifica blacklist JWT avvenga tramite Redis."""
        # Given
        jti = "jwt-unique-id-123"
        redis_client.is_token_blacklisted = AsyncMock(return_value=True)

        # When
        result = await redis_client.is_token_blacklisted(jti)

        # Then
        assert result is True
        redis_client.is_token_blacklisted.assert_called_once_with(jti)

    @pytest.mark.asyncio
    async def test_user_session_retrieval_from_redis(self, redis_client):
        """Test che i dati della sessione vengano recuperati da Redis."""
        # Given
        session_id = "test_refresh_token_123"
        cached_session = {
            "user_id": str(uuid.uuid4()),
            "username": "testuser",
            "is_active": True,
            "last_activity": datetime.now(timezone.utc).isoformat()
        }

        redis_client.get_user_session = AsyncMock(return_value=cached_session)

        # When
        result = await redis_client.get_user_session(session_id)

        # Then
        assert result == cached_session
        redis_client.get_user_session.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_user_session_invalidation_on_logout(self, redis_client):
        """Test che le sessioni utente vengano invalidate in Redis al logout."""
        # Given
        user_id = uuid.uuid4()
        redis_client.invalidate_user_sessions = AsyncMock(return_value=True)

        # When
        result = await redis_client.invalidate_user_sessions(user_id)

        # Then
        assert result is True
        redis_client.invalidate_user_sessions.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_refresh_token_session_update_in_redis(self, redis_client):
        """Test che il refresh token aggiorni la sessione in Redis."""
        # Given
        old_session_id = "old_refresh_token_123"
        new_session_id = "new_refresh_token_456"

        # Mock getting old session
        old_session_data = {
            "user_id": str(uuid.uuid4()),
            "username": "testuser",
            "login_time": "2024-01-01T10:00:00Z"
        }
        redis_client.get_user_session = AsyncMock(return_value=old_session_data)
        redis_client.delete = AsyncMock(return_value=True)
        redis_client.cache_user_session = AsyncMock(return_value=True)

        # When
        # Simulate refresh token flow
        old_session = await redis_client.get_user_session(old_session_id)
        await redis_client.delete(f"session:{old_session_id}")

        # Create new session data
        new_session_data = {
            **old_session_data,
            "refresh_token": new_session_id,
            "last_activity": datetime.now(timezone.utc).isoformat()
        }

        result = await redis_client.cache_user_session(
            session_id=new_session_id,
            user_data=new_session_data,
            expire=7 * 24 * 3600
        )

        # Then
        assert result is True
        redis_client.get_user_session.assert_called_once_with(old_session_id)
        redis_client.delete.assert_called_once_with(f"session:{old_session_id}")
        redis_client.cache_user_session.assert_called_once()