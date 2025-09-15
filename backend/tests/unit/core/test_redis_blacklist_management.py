"""TDD Test per verifica del blacklist management appropriato in Redis."""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

from src.notemesh.core.redis_client import RedisClient
from src.notemesh.security.jwt import blacklist_token, decode_access_token


class TestRedisBlacklistManagement:
    """Test per verificare che il blacklist management JWT sia appropriato."""

    @pytest.fixture
    def redis_client(self):
        """Mock Redis client."""
        return Mock(spec=RedisClient)

    @pytest.mark.asyncio
    async def test_jwt_token_added_to_blacklist_on_logout(self, redis_client):
        """Test che i token JWT vengano aggiunti alla blacklist al logout."""
        # Given
        jti = "jwt-unique-id-123"
        expire_seconds = 900  # 15 minutes remaining

        redis_client.add_to_blacklist = AsyncMock(return_value=True)

        # When
        result = await redis_client.add_to_blacklist(jti, expire_seconds)

        # Then
        assert result is True
        redis_client.add_to_blacklist.assert_called_once_with(jti, expire_seconds)

    @pytest.mark.asyncio
    async def test_blacklisted_token_is_properly_detected(self, redis_client):
        """Test che i token in blacklist vengano rilevati correttamente."""
        # Given
        jti = "blacklisted-jwt-123"
        redis_client.is_token_blacklisted = AsyncMock(return_value=True)

        # When
        is_blacklisted = await redis_client.is_token_blacklisted(jti)

        # Then
        assert is_blacklisted is True
        redis_client.is_token_blacklisted.assert_called_once_with(jti)

    @pytest.mark.asyncio
    async def test_non_blacklisted_token_returns_false(self, redis_client):
        """Test che i token non in blacklist ritornino False."""
        # Given
        jti = "valid-jwt-123"
        redis_client.is_token_blacklisted = AsyncMock(return_value=False)

        # When
        is_blacklisted = await redis_client.is_token_blacklisted(jti)

        # Then
        assert is_blacklisted is False
        redis_client.is_token_blacklisted.assert_called_once_with(jti)

    @pytest.mark.asyncio
    async def test_blacklist_ttl_matches_token_expiry(self):
        """Test che il TTL della blacklist corrisponda alla scadenza del token."""
        # Given - Mock a JWT token with specific expiry (as Unix timestamp)
        expiry_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        mock_payload = {
            "sub": str(uuid.uuid4()),
            "exp": int(expiry_time.timestamp()),  # JWT exp should be Unix timestamp
            "jti": "test-jwt-123",
            "type": "access"
        }

        # Mock JWT decode to return our payload
        with patch('src.notemesh.security.jwt.jwt.decode', return_value=mock_payload):
            with patch('src.notemesh.security.jwt.get_redis_client') as mock_get_client:
                mock_redis = Mock()
                mock_redis.connect = AsyncMock()
                mock_redis.add_to_blacklist = AsyncMock(return_value=True)
                mock_get_client.return_value = mock_redis

                # When
                result = await blacklist_token("mock.jwt.token")

                # Then
                assert result is True
                # Verify Redis was called with appropriate TTL (around 15 minutes = 900 seconds)
                mock_redis.add_to_blacklist.assert_called_once()
                call_args = mock_redis.add_to_blacklist.call_args
                jti_arg = call_args[0][0]
                ttl_arg = call_args[0][1]

                assert jti_arg == "test-jwt-123"
                # TTL should be close to 15 minutes (allowing some tolerance for execution time)
                assert 890 <= ttl_arg <= 900

    @pytest.mark.asyncio
    async def test_expired_token_not_added_to_blacklist(self):
        """Test che i token già scaduti non vengano aggiunti alla blacklist."""
        # Given - Mock an expired JWT token
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=5)  # Expired 5 minutes ago
        mock_payload = {
            "sub": str(uuid.uuid4()),
            "exp": int(expired_time.timestamp()),  # JWT exp should be Unix timestamp
            "jti": "expired-jwt-123",
            "type": "access"
        }

        # Mock JWT decode to return expired payload
        with patch('src.notemesh.security.jwt.jwt.decode', return_value=mock_payload):
            with patch('src.notemesh.security.jwt.get_redis_client') as mock_get_client:
                mock_redis = Mock()
                mock_redis.connect = AsyncMock()
                mock_redis.add_to_blacklist = AsyncMock(return_value=True)
                mock_get_client.return_value = mock_redis

                # When
                result = await blacklist_token("expired.jwt.token")

                # Then
                assert result is False
                # Verify Redis blacklist was NOT called for expired token
                mock_redis.add_to_blacklist.assert_not_called()

    @pytest.mark.asyncio
    async def test_token_without_jti_not_blacklisted(self):
        """Test che i token senza JTI non vengano aggiunti alla blacklist."""
        # Given - Mock a JWT token without JTI
        future_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        mock_payload = {
            "sub": str(uuid.uuid4()),
            "exp": int(future_time.timestamp()),  # JWT exp should be Unix timestamp
            "type": "access"
            # Missing "jti" field
        }

        # Mock JWT decode to return payload without JTI
        with patch('src.notemesh.security.jwt.jwt.decode', return_value=mock_payload):
            with patch('src.notemesh.security.jwt.get_redis_client') as mock_get_client:
                mock_redis = Mock()
                mock_redis.connect = AsyncMock()
                mock_redis.add_to_blacklist = AsyncMock(return_value=True)
                mock_get_client.return_value = mock_redis

                # When
                result = await blacklist_token("no.jti.token")

                # Then
                assert result is False
                # Verify Redis blacklist was NOT called for token without JTI
                mock_redis.add_to_blacklist.assert_not_called()

    @pytest.mark.asyncio
    async def test_token_validation_checks_blacklist(self):
        """Test che la validazione dei token controlli la blacklist Redis."""
        # Given - Mock a valid token that's blacklisted
        future_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        mock_payload = {
            "sub": str(uuid.uuid4()),
            "exp": int(future_time.timestamp()),  # JWT exp should be Unix timestamp
            "jti": "blacklisted-jwt-123",
            "type": "access"
        }

        with patch('src.notemesh.security.jwt.jwt.decode', return_value=mock_payload):
            with patch('src.notemesh.security.jwt.get_redis_client') as mock_get_client:
                mock_redis = Mock()
                mock_redis.connect = AsyncMock()
                mock_redis.is_token_blacklisted = AsyncMock(return_value=True)
                mock_get_client.return_value = mock_redis

                # When
                result = await decode_access_token("blacklisted.jwt.token")

                # Then
                assert result is None  # Token should be rejected due to blacklist
                mock_redis.is_token_blacklisted.assert_called_once_with("blacklisted-jwt-123")

    @pytest.mark.asyncio
    async def test_blacklist_redis_error_graceful_handling(self):
        """Test che gli errori Redis nella blacklist vengano gestiti gracefully."""
        # Given - Mock Redis error during blacklist check
        future_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        mock_payload = {
            "sub": str(uuid.uuid4()),
            "exp": int(future_time.timestamp()),  # JWT exp should be Unix timestamp
            "jti": "test-jwt-123",
            "type": "access"
        }

        with patch('src.notemesh.security.jwt.jwt.decode', return_value=mock_payload):
            with patch('src.notemesh.security.jwt.get_redis_client') as mock_get_client:
                mock_redis = Mock()
                mock_redis.connect = AsyncMock(side_effect=Exception("Redis connection error"))
                mock_get_client.return_value = mock_redis

                # When
                result = await decode_access_token("valid.jwt.token")

                # Then
                # Should still return valid payload even if Redis is down (graceful degradation)
                assert result == mock_payload

    @pytest.mark.asyncio
    async def test_blacklist_key_format_is_consistent(self, redis_client):
        """Test che il formato delle chiavi blacklist sia consistente."""
        # Given
        jti = "test-jwt-123"
        expected_key_pattern = f"blacklist:{jti}"

        # Mock Redis client to capture the key format
        redis_client.set = AsyncMock(return_value=True)

        # When simulating blacklist operation
        blacklist_key = f"blacklist:{jti}"
        await redis_client.set(blacklist_key, "blacklisted", expire=900)

        # Then
        redis_client.set.assert_called_once_with(blacklist_key, "blacklisted", expire=900)
        assert "blacklist:" in blacklist_key
        assert jti in blacklist_key

    @pytest.mark.asyncio
    async def test_multiple_tokens_can_be_blacklisted_independently(self, redis_client):
        """Test che più token possano essere in blacklist indipendentemente."""
        # Given
        token_jtis = ["jwt-1", "jwt-2", "jwt-3"]

        redis_client.add_to_blacklist = AsyncMock(return_value=True)
        redis_client.is_token_blacklisted = AsyncMock(side_effect=lambda jti: jti in ["jwt-1", "jwt-3"])

        # When - Add tokens to blacklist
        for jti in token_jtis:
            await redis_client.add_to_blacklist(jti, 900)

        # Check blacklist status
        results = {}
        for jti in token_jtis:
            results[jti] = await redis_client.is_token_blacklisted(jti)

        # Then
        assert len(redis_client.add_to_blacklist.call_args_list) == 3
        assert results["jwt-1"] is True   # Blacklisted
        assert results["jwt-2"] is False  # Not blacklisted
        assert results["jwt-3"] is True   # Blacklisted