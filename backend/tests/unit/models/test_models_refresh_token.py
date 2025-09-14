"""
Unit tests for RefreshToken model.
"""

import pytest
import uuid
from datetime import datetime, timedelta

from src.notemesh.core.models.user import User
from src.notemesh.core.models.refresh_token import RefreshToken


class TestRefreshTokenModel:
    """Test RefreshToken model functionality."""
    
    @pytest.mark.asyncio
    async def test_create_refresh_token(self, test_session, test_user):
        """Test creating a refresh token."""
        token = RefreshToken(
            token="test_token_12345",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7),
            device_identifier="iPhone 12",
            created_from_ip="192.168.1.1"
        )
        
        test_session.add(token)
        await test_session.commit()
        await test_session.refresh(token)
        
        assert token.id is not None
        assert token.token == "test_token_12345"
        assert token.user_id == test_user.id
        assert token.is_active is True
        assert token.device_identifier == "iPhone 12"
        assert token.created_from_ip == "192.168.1.1"
        assert token.last_used_at is None
        assert token.revoked_at is None
        assert token.revocation_reason is None
        assert isinstance(token.token_family_id, uuid.UUID)
    
    @pytest.mark.asyncio
    async def test_refresh_token_defaults(self, test_session, test_user):
        """Test refresh token with default values."""
        expires = datetime.utcnow() + timedelta(days=7)
        
        token = RefreshToken(
            token="minimal_token",
            user_id=test_user.id,
            expires_at=expires
        )
        
        test_session.add(token)
        await test_session.commit()
        await test_session.refresh(token)
        
        assert token.device_identifier is None
        assert token.is_active is True
        assert token.created_from_ip is None
        assert isinstance(token.token_family_id, uuid.UUID)
    
    @pytest.mark.asyncio
    async def test_refresh_token_repr(self, test_session, test_user):
        """Test refresh token string representation."""
        token = RefreshToken(
            token="abcdefghijklmnop",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        test_session.add(token)
        await test_session.commit()
        
        expected = f"<RefreshToken(user_id={test_user.id}, token=abcdefgh..., active=True)>"
        assert repr(token) == expected
    
    @pytest.mark.asyncio
    async def test_refresh_token_repr_short_token(self, test_session, test_user):
        """Test refresh token repr with short token."""
        token = RefreshToken(
            token="short",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        test_session.add(token)
        await test_session.commit()
        
        # Short tokens should still show preview
        expected = f"<RefreshToken(user_id={test_user.id}, token=short..., active=True)>"
        assert repr(token) == expected
    
    @pytest.mark.asyncio
    async def test_generate_secure_token(self):
        """Test secure token generation."""
        token1 = RefreshToken.generate_secure_token()
        token2 = RefreshToken.generate_secure_token()
        
        # Should be strings
        assert isinstance(token1, str)
        assert isinstance(token2, str)
        
        # Should be unique
        assert token1 != token2
        
        # Should have reasonable length (base64 encoded)
        assert len(token1) > 20
        assert len(token2) > 20
    
    @pytest.mark.asyncio
    async def test_create_for_user(self, test_session, test_user):
        """Test create_for_user class method."""
        token = RefreshToken.create_for_user(
            user_id=test_user.id,
            device_id="iPad Pro",
            ip="10.0.0.1",
            expires_days=14
        )
        
        test_session.add(token)
        await test_session.commit()
        await test_session.refresh(token)
        
        assert token.user_id == test_user.id
        assert token.device_identifier == "iPad Pro"
        assert token.created_from_ip == "10.0.0.1"
        assert token.is_active is True
        
        # Check expiration is roughly 14 days from now
        expected_expiry = datetime.utcnow() + timedelta(days=14)
        diff = abs((token.expires_at - expected_expiry).total_seconds())
        assert diff < 60  # Within 1 minute
        
        # Token should be generated
        assert len(token.token) > 20
    
    @pytest.mark.asyncio
    async def test_refresh_token_unique_token(self, test_session, test_user):
        """Test that token must be unique."""
        token1 = RefreshToken(
            token="duplicate_token",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        token2 = RefreshToken(
            token="duplicate_token",  # Same token
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        test_session.add(token1)
        await test_session.commit()
        
        test_session.add(token2)
        
        # Should raise integrity error
        with pytest.raises(Exception):
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_refresh_token_is_expired(self, test_session, test_user):
        """Test is_expired property."""
        # Create expired token
        expired_token = RefreshToken(
            token="expired_token",
            user_id=test_user.id,
            expires_at=datetime.utcnow() - timedelta(hours=1),
            is_active=True
        )
        
        test_session.add(expired_token)
        await test_session.commit()
        
        assert expired_token.is_expired is True
        
        # Create valid token
        valid_token = RefreshToken(
            token="valid_token",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True
        )
        
        test_session.add(valid_token)
        await test_session.commit()
        
        assert valid_token.is_expired is False
    
    @pytest.mark.asyncio
    async def test_refresh_token_is_valid(self, test_session, test_user):
        """Test is_valid property."""
        # Active and not expired
        valid_token = RefreshToken(
            token="valid",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=1),
            is_active=True
        )
        
        test_session.add(valid_token)
        await test_session.commit()
        
        assert valid_token.is_valid is True
        
        # Inactive
        inactive_token = RefreshToken(
            token="inactive",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=1),
            is_active=False
        )
        
        test_session.add(inactive_token)
        await test_session.commit()
        
        assert inactive_token.is_valid is False
        
        # Expired
        expired_token = RefreshToken(
            token="expired",
            user_id=test_user.id,
            expires_at=datetime.utcnow() - timedelta(days=1),
            is_active=True
        )
        
        test_session.add(expired_token)
        await test_session.commit()
        
        assert expired_token.is_valid is False
    
    @pytest.mark.asyncio
    async def test_refresh_token_revoke(self, test_session, test_user):
        """Test revoke method."""
        token = RefreshToken(
            token="to_revoke",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        test_session.add(token)
        await test_session.commit()
        
        # Revoke the token
        token.revoke("Suspicious activity")
        await test_session.commit()
        await test_session.refresh(token)
        
        assert token.is_active is False
        assert token.revoked_at is not None
        assert isinstance(token.revoked_at, datetime)
        assert token.revocation_reason == "Suspicious activity"
    
    @pytest.mark.asyncio
    async def test_refresh_token_record_usage(self, test_session, test_user):
        """Test record_usage method."""
        token = RefreshToken(
            token="used_token",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        test_session.add(token)
        await test_session.commit()
        
        # Record usage
        token.record_usage()
        await test_session.commit()
        await test_session.refresh(token)
        
        assert token.last_used_at is not None
        assert isinstance(token.last_used_at, datetime)
    
    @pytest.mark.asyncio
    async def test_refresh_token_user_relationship(self, test_session, test_user):
        """Test refresh token user relationship."""
        token = RefreshToken(
            token="related_token",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        
        test_session.add(token)
        await test_session.commit()
        await test_session.refresh(token)
        
        assert token.user == test_user
        assert token.user.username == test_user.username
    
    @pytest.mark.asyncio
    async def test_refresh_token_cascade_delete(self, test_session):
        """Test cascade delete when user is deleted."""
        # Create user
        user = User(username="tokenuser", password_hash="hash")
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        # Create token
        token = RefreshToken(
            token="cascade_test",
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        test_session.add(token)
        await test_session.commit()
        
        token_id = token.id
        
        # Delete user - token should be deleted
        await test_session.delete(user)
        await test_session.commit()
        
        deleted_token = await test_session.get(RefreshToken, token_id)
        assert deleted_token is None
    
    @pytest.mark.asyncio
    async def test_refresh_token_ipv6_support(self, test_session, test_user):
        """Test IPv6 address support."""
        token = RefreshToken(
            token="ipv6_token",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7),
            created_from_ip="2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        )
        
        test_session.add(token)
        await test_session.commit()
        await test_session.refresh(token)
        
        assert token.created_from_ip == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    
    @pytest.mark.asyncio
    async def test_refresh_token_field_constraints(self, test_session, test_user):
        """Test field constraints."""
        # Token too long (max 255)
        with pytest.raises(Exception):
            token = RefreshToken(
                token="a" * 256,  # Too long
                user_id=test_user.id,
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            test_session.add(token)
            await test_session.commit()
        
        await test_session.rollback()
        
        # Device identifier too long (max 255)
        with pytest.raises(Exception):
            token = RefreshToken(
                token="valid_token",
                user_id=test_user.id,
                expires_at=datetime.utcnow() + timedelta(days=7),
                device_identifier="a" * 256  # Too long
            )
            test_session.add(token)
            await test_session.commit()
        
        await test_session.rollback()
        
        # IP address too long (max 45 for IPv6)
        with pytest.raises(Exception):
            token = RefreshToken(
                token="valid_token2",
                user_id=test_user.id,
                expires_at=datetime.utcnow() + timedelta(days=7),
                created_from_ip="a" * 46  # Too long
            )
            test_session.add(token)
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_refresh_token_family(self, test_session, test_user):
        """Test token family functionality."""
        family_id = uuid.uuid4()
        
        # Create tokens in same family
        token1 = RefreshToken(
            token="family_token1",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7),
            token_family_id=family_id
        )
        
        token2 = RefreshToken(
            token="family_token2",
            user_id=test_user.id,
            expires_at=datetime.utcnow() + timedelta(days=7),
            token_family_id=family_id
        )
        
        test_session.add_all([token1, token2])
        await test_session.commit()
        
        assert token1.token_family_id == token2.token_family_id
        assert token1.token_family_id == family_id