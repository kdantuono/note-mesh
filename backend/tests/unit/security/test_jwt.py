"""Unit tests for security/jwt.py"""

from datetime import timedelta
import uuid

from jose import jwt

from src.notemesh.security.jwt import (
    create_access_token,
    decode_access_token,
    get_user_id_from_token,
    create_refresh_token,
)


class DummySettings:
    secret_key = "test-secret"
    algorithm = "HS256"
    access_token_expire_minutes = 30


def test_create_and_decode_access_token(monkeypatch):
    # Patch settings to deterministic values
    from src.notemesh.security import jwt as jwt_module
    monkeypatch.setattr(jwt_module, "get_settings", lambda: DummySettings())

    sub = str(uuid.uuid4())
    token = create_access_token({"sub": sub}, expires_delta=timedelta(minutes=5))
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("sub") == sub
    assert payload.get("type") == "access"


def test_decode_access_token_invalid_signature(monkeypatch):
    from src.notemesh.security import jwt as jwt_module
    monkeypatch.setattr(jwt_module, "get_settings", lambda: DummySettings())

    # Create token with different secret to simulate invalid signature
    other_secret = "wrong-secret"
    sub = str(uuid.uuid4())
    token = jwt.encode({"sub": sub, "type": "access"}, other_secret, algorithm=DummySettings.algorithm)

    assert decode_access_token(token) is None


def test_get_user_id_from_token(monkeypatch):
    from src.notemesh.security import jwt as jwt_module
    monkeypatch.setattr(jwt_module, "get_settings", lambda: DummySettings())

    sub = str(uuid.uuid4())
    token = create_access_token({"sub": sub})
    uid = get_user_id_from_token(token)
    assert str(uid) == sub


def test_get_user_id_from_token_invalid_payload(monkeypatch):
    from src.notemesh.security import jwt as jwt_module
    monkeypatch.setattr(jwt_module, "get_settings", lambda: DummySettings())

    token = create_access_token({})
    assert get_user_id_from_token(token) is None


def test_create_refresh_token():
    token = create_refresh_token()
    assert isinstance(token, str)
    assert len(token) > 20
