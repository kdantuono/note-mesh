"""
Unit tests for JWT token utilities.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID
from unittest.mock import patch

from jose import jwt

from src.notemesh.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_user_id_from_token,
)
from src.notemesh.config import Settings


class TestJWTUtils:
    """Test JWT token creation and validation."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        return Settings(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=30,
        )
    
    def test_create_access_token(self, mock_settings):
        """Test creating access token."""
        with patch("src.notemesh.security.jwt.get_settings", return_value=mock_settings):
            user_id = str(uuid4())
            data = {"sub": user_id}
            
            token = create_access_token(data)
            
            # Verify token is a string
            assert isinstance(token, str)
            assert len(token) > 0
            
            # Decode and verify token content
            decoded = jwt.decode(
                token,
                mock_settings.secret_key,
                algorithms=[mock_settings.algorithm]
            )
            
            assert decoded["sub"] == user_id
            assert decoded["type"] == "access"
            assert "exp" in decoded
    
    def test_create_access_token_with_custom_expiry(self, mock_settings):
        """Test creating access token with custom expiry."""
        with patch("src.notemesh.security.jwt.get_settings", return_value=mock_settings):
            user_id = str(uuid4())
            data = {"sub": user_id}
            expires_delta = timedelta(hours=1)
            
            token = create_access_token(data, expires_delta=expires_delta)
            
            decoded = jwt.decode(
                token,
                mock_settings.secret_key,
                algorithms=[mock_settings.algorithm]
            )
            
            # Check expiry is roughly 1 hour from now
            exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
            expected_exp = datetime.now(timezone.utc) + expires_delta
            
            # Allow 5 seconds difference for test execution time
            assert abs((exp_time - expected_exp).total_seconds()) < 5
    
    def test_create_access_token_with_additional_data(self, mock_settings):
        """Test creating access token with additional claims."""
        with patch("src.notemesh.security.jwt.get_settings", return_value=mock_settings):
            user_id = str(uuid4())
            data = {
                "sub": user_id,
                "username": "testuser",
                "roles": ["user", "admin"],
            }
            
            token = create_access_token(data)
            decoded = jwt.decode(
                token,
                mock_settings.secret_key,
                algorithms=[mock_settings.algorithm]
            )
            
            assert decoded["sub"] == user_id
            assert decoded["username"] == "testuser"
            assert decoded["roles"] == ["user", "admin"]
    
    def test_create_refresh_token(self):
        """Test creating refresh token."""
        token1 = create_refresh_token()
        token2 = create_refresh_token()
        
        # Should be URL-safe strings
        assert isinstance(token1, str)
        assert isinstance(token2, str)
        
        # Should be unique
        assert token1 != token2
        
        # Should have reasonable length (32 bytes base64 encoded)
        assert len(token1) > 20
    
    def test_decode_access_token_valid(self, mock_settings):
        """Test decoding valid access token."""
        with patch("src.notemesh.security.jwt.get_settings", return_value=mock_settings):
            user_id = str(uuid4())
            data = {"sub": user_id}
            token = create_access_token(data)
            
            decoded = decode_access_token(token)
            
            assert decoded is not None
            assert decoded["sub"] == user_id
            assert decoded["type"] == "access"
    
    def test_decode_access_token_invalid(self, mock_settings):
        """Test decoding invalid access token."""
        with patch("src.notemesh.security.jwt.get_settings", return_value=mock_settings):
            # Invalid token
            assert decode_access_token("invalid.token.here") is None
            
            # Empty token
            assert decode_access_token("") is None
    
    def test_decode_access_token_wrong_type(self, mock_settings):
        """Test decoding token with wrong type."""
        with patch("src.notemesh.security.jwt.get_settings", return_value=mock_settings):
            # Create token with wrong type
            data = {"sub": str(uuid4()), "type": "refresh"}
            token = jwt.encode(
                data,
                mock_settings.secret_key,
                algorithm=mock_settings.algorithm
            )
            
            assert decode_access_token(token) is None
    
    def test_decode_access_token_expired(self, mock_settings):
        """Test decoding expired access token."""
        with patch("src.notemesh.security.jwt.get_settings", return_value=mock_settings):
            user_id = str(uuid4())
            data = {"sub": user_id}
            # Create token that expires immediately
            token = create_access_token(data, expires_delta=timedelta(seconds=-1))
            
            assert decode_access_token(token) is None
    
    def test_decode_access_token_wrong_secret(self, mock_settings):
        """Test decoding token with wrong secret."""
        with patch("src.notemesh.security.jwt.get_settings", return_value=mock_settings):
            user_id = str(uuid4())
            data = {"sub": user_id, "type": "access"}
            
            # Create token with different secret
            token = jwt.encode(
                data,
                "wrong-secret-key",
                algorithm=mock_settings.algorithm
            )
            
            assert decode_access_token(token) is None
    
    def test_get_user_id_from_token_valid(self, mock_settings):
        """Test extracting user ID from valid token."""
        with patch("src.notemesh.security.jwt.get_settings", return_value=mock_settings):
            user_id = uuid4()
            data = {"sub": str(user_id)}
            token = create_access_token(data)
            
            extracted_id = get_user_id_from_token(token)
            
            assert extracted_id == user_id
            assert isinstance(extracted_id, UUID)
    
    def test_get_user_id_from_token_invalid(self, mock_settings):
        """Test extracting user ID from invalid token."""
        with patch("src.notemesh.security.jwt.get_settings", return_value=mock_settings):
            # Invalid token
            assert get_user_id_from_token("invalid.token") is None
            
            # Token without sub claim
            data = {"username": "testuser"}
            token = create_access_token(data)
            assert get_user_id_from_token(token) is None
            
            # Token with invalid UUID
            data = {"sub": "not-a-uuid"}
            token = create_access_token(data)
            assert get_user_id_from_token(token) is None
    
    def test_get_user_id_from_token_non_uuid_sub(self, mock_settings):
        """Test extracting user ID when sub is not a valid UUID."""
        with patch("src.notemesh.security.jwt.get_settings", return_value=mock_settings):
            data = {"sub": "12345"}  # Not a valid UUID
            token = create_access_token(data)
            
            assert get_user_id_from_token(token) is None