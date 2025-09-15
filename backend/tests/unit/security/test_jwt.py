"""Unit tests for security/jwt.py"""

import uuid
from datetime import timedelta

from jose import jwt

from src.notemesh.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_user_id_from_token,
)


class DummySettings:
    secret_key = "test-secret"
    algorithm = "HS256"
    access_token_expire_minutes = 30


async def test_create_and_decode_access_token(monkeypatch):
    # Patch settings to deterministic values
    from src.notemesh.security import jwt as jwt_module

    monkeypatch.setattr(jwt_module, "get_settings", lambda: DummySettings())

    # Mock Redis client: sync factory returning object with async methods
    def mock_get_redis_client():
        class MockRedis:
            async def connect(self):
                pass
            async def is_token_blacklisted(self, jti):
                return False
        return MockRedis()

    monkeypatch.setattr(jwt_module, "get_redis_client", mock_get_redis_client)

    sub = str(uuid.uuid4())
    token = create_access_token({"sub": sub}, expires_delta=timedelta(minutes=5))
    assert isinstance(token, str)

    payload = await decode_access_token(token)
    assert payload is not None
    assert payload.get("sub") == sub
    assert payload.get("type") == "access"


async def test_decode_access_token_invalid_signature(monkeypatch):
    from src.notemesh.security import jwt as jwt_module

    monkeypatch.setattr(jwt_module, "get_settings", lambda: DummySettings())

    # Mock Redis client: sync factory returning object with async methods
    def mock_get_redis_client():
        class MockRedis:
            async def connect(self):
                pass
            async def is_token_blacklisted(self, jti):
                return False
        return MockRedis()

    monkeypatch.setattr(jwt_module, "get_redis_client", mock_get_redis_client)

    # Create token with different secret to simulate invalid signature
    other_secret = "wrong-secret"
    sub = str(uuid.uuid4())
    token = jwt.encode(
        {"sub": sub, "type": "access"}, other_secret, algorithm=DummySettings.algorithm
    )

    assert await decode_access_token(token) is None


async def test_get_user_id_from_token(monkeypatch):
    from src.notemesh.security import jwt as jwt_module

    monkeypatch.setattr(jwt_module, "get_settings", lambda: DummySettings())

    # Mock Redis client: sync factory returning object with async methods
    def mock_get_redis_client():
        class MockRedis:
            async def connect(self):
                pass
            async def is_token_blacklisted(self, jti):
                return False
        return MockRedis()

    monkeypatch.setattr(jwt_module, "get_redis_client", mock_get_redis_client)

    sub = str(uuid.uuid4())
    token = create_access_token({"sub": sub})
    uid = await get_user_id_from_token(token)
    assert str(uid) == sub


async def test_get_user_id_from_token_invalid_payload(monkeypatch):
    from src.notemesh.security import jwt as jwt_module

    monkeypatch.setattr(jwt_module, "get_settings", lambda: DummySettings())

    # Mock Redis client: sync factory returning object with async methods
    def mock_get_redis_client():
        class MockRedis:
            async def connect(self):
                pass
            async def is_token_blacklisted(self, jti):
                return False
        return MockRedis()

    monkeypatch.setattr(jwt_module, "get_redis_client", mock_get_redis_client)

    token = create_access_token({})
    assert await get_user_id_from_token(token) is None


def test_create_refresh_token():
    token = create_refresh_token()
    assert isinstance(token, str)
    assert len(token) > 20
