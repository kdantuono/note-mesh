"""Unit tests for AuthService (src/notemesh/core/services/auth_service.py)."""

import uuid
from datetime import datetime, timezone

import pytest

from src.notemesh.core.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    RegisterRequest,
)
from src.notemesh.core.services.auth_service import AuthService


class DummyUser:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def can_login(self):
        return self.__dict__.get("is_active", True)


@pytest.mark.asyncio
async def test_register_user(monkeypatch):
    class FakeUserRepo:
        async def is_username_taken(self, username):
            return False

        async def create_user(self, user_data):
            return DummyUser(
                id=uuid.uuid4(),
                username=user_data["username"],
                full_name=user_data.get("full_name"),
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

    class FakeTokenRepo:
        pass

    # Patch repositories in service
    from src.notemesh.core import services as services_pkg

    monkeypatch.setattr(services_pkg.auth_service, "UserRepository", lambda s: FakeUserRepo())
    monkeypatch.setattr(
        services_pkg.auth_service, "RefreshTokenRepository", lambda s: FakeTokenRepo()
    )

    # Patch hashing to be deterministic
    from src.notemesh import security as security_pkg

    monkeypatch.setattr(security_pkg, "hash_password", lambda p: "hashed")

    svc = AuthService(session=None)
    req = RegisterRequest(
        username="alice",
        password="Password123!",
        confirm_password="Password123!",
        full_name="Alice",
    )
    res = await svc.register_user(req)
    assert res.username == "alice"


@pytest.mark.asyncio
async def test_authenticate_user_success(monkeypatch):
    user_id = uuid.uuid4()

    class FakeUserRepo:
        async def get_by_username(self, username):
            return DummyUser(
                id=user_id,
                username=username,
                full_name=None,
                is_active=True,
                password_hash="hashed",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

    class FakeTokenRepo:
        async def create_token(self, data):
            return True

    from src.notemesh.core import services as services_pkg

    monkeypatch.setattr(services_pkg.auth_service, "UserRepository", lambda s: FakeUserRepo())
    monkeypatch.setattr(
        services_pkg.auth_service, "RefreshTokenRepository", lambda s: FakeTokenRepo()
    )

    # Patch the symbols as used inside auth_service module
    from src.notemesh.core.services import auth_service as auth_service_module

    monkeypatch.setattr(auth_service_module, "verify_password", lambda p, h: True)
    monkeypatch.setattr(auth_service_module, "create_access_token", lambda data: "at")
    monkeypatch.setattr(auth_service_module, "create_refresh_token", lambda: "rt")

    svc = AuthService(session=None)
    res = await svc.authenticate_user(LoginRequest(username="bob", password="Password123!"))
    assert res.access_token == "at"
    assert res.refresh_token == "rt"
    assert str(res.user.id) == str(user_id)


@pytest.mark.asyncio
async def test_refresh_token_flow(monkeypatch):
    user_id = uuid.uuid4()

    class FakeTokenRepo:
        async def is_token_valid(self, token):
            return token == "valid"

        async def get_by_token(self, token):
            # Bind user_id into local scope to avoid NameError in class body
            _uid = user_id

            class T:
                user_id = _uid

            return T()

        async def delete_token(self, token):
            return True

        async def create_token(self, data):
            return True

    class FakeUserRepo:
        async def get_by_id(self, uid):
            return DummyUser(
                id=uid,
                username="bob",
                full_name=None,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

    from src.notemesh.core import services as services_pkg

    monkeypatch.setattr(
        services_pkg.auth_service, "RefreshTokenRepository", lambda s: FakeTokenRepo()
    )
    monkeypatch.setattr(services_pkg.auth_service, "UserRepository", lambda s: FakeUserRepo())

    from src.notemesh.core.services import auth_service as auth_service_module

    monkeypatch.setattr(auth_service_module, "create_access_token", lambda data: "new-at")
    monkeypatch.setattr(auth_service_module, "create_refresh_token", lambda: "new-rt")

    svc = AuthService(session=None)
    res = await svc.refresh_token(RefreshTokenRequest(refresh_token="valid"))
    assert res.access_token == "new-at"
    assert res.refresh_token == "new-rt"


@pytest.mark.asyncio
async def test_change_password_revokes_tokens(monkeypatch):
    uid = uuid.uuid4()

    class FakeUserRepo:
        async def get_by_id(self, user_id):
            return DummyUser(
                id=user_id,
                username="x",
                password_hash="hashed",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

        async def update_user(self, user_id, data):
            return True

    class FakeTokenRepo:
        async def delete_user_tokens(self, user_id):
            return 1

    from src.notemesh.core import services as services_pkg

    monkeypatch.setattr(services_pkg.auth_service, "UserRepository", lambda s: FakeUserRepo())
    monkeypatch.setattr(
        services_pkg.auth_service, "RefreshTokenRepository", lambda s: FakeTokenRepo()
    )

    from src.notemesh.core.services import auth_service as auth_service_module

    monkeypatch.setattr(auth_service_module, "verify_password", lambda p, h: True)
    monkeypatch.setattr(auth_service_module, "hash_password", lambda p: "new-hash")

    svc = AuthService(session=None)
    ok = await svc.change_password(
        uid,
        PasswordChangeRequest(
            current_password="old", new_password="newPass123!", confirm_new_password="newPass123!"
        ),
    )
    assert ok is True
