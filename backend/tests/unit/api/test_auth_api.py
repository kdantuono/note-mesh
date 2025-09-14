"""Unit tests for auth API router (src/notemesh/api/auth.py)."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.notemesh.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _json_ok(resp) -> dict[str, Any]:
    assert resp.status_code in (200, 201)
    return resp.json()


def test_register_calls_service(monkeypatch, client):
    called = {}

    async def fake_register_user(self, request):
        called["request"] = request
        return {
            "id": str(uuid.uuid4()),
            "username": request.username,
            "full_name": request.full_name,
            "is_active": True,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

    from src.notemesh.core.services.auth_service import AuthService
    monkeypatch.setattr(AuthService, "register_user", fake_register_user, raising=True)

    payload = {
        "username": "alice",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "full_name": "Alice A"
    }
    resp = client.post("/api/auth/register", json=payload)
    data = _json_ok(resp)
    assert data["username"] == "alice"


def test_login_calls_service(monkeypatch, client):
    async def fake_auth(self, request):
        return {
            "access_token": "at",
            "refresh_token": "rt",
            "token_type": "bearer",
            "expires_in": 900,
            "user": {
                "id": str(uuid.uuid4()),
                "username": request.username,
                "full_name": None,
                "is_active": True,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            },
        }

    from src.notemesh.core.services.auth_service import AuthService
    monkeypatch.setattr(AuthService, "authenticate_user", fake_auth, raising=True)

    resp = client.post("/api/auth/login", json={"username": "bob", "password": "Password123!"})
    data = _json_ok(resp)
    assert data["token_type"] == "bearer"


def test_refresh_calls_service(monkeypatch, client):
    async def fake_refresh(self, request):
        return {
            "access_token": "new-at",
            "refresh_token": "new-rt",
            "token_type": "bearer",
            "expires_in": 900,
            "user": {
                "id": str(uuid.uuid4()),
                "username": "bob",
                "full_name": None,
                "is_active": True,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            },
        }

    from src.notemesh.core.services.auth_service import AuthService
    monkeypatch.setattr(AuthService, "refresh_token", fake_refresh, raising=True)

    resp = client.post("/api/auth/refresh", json={"refresh_token": "rt"})
    data = _json_ok(resp)
    assert data["access_token"] == "new-at"


def test_me_calls_service(monkeypatch, client):
    user_id = uuid.uuid4()

    async def fake_get_current_user(self, uid):
        assert str(uid) == str(user_id)
        return {
            "id": str(uid),
            "username": "bob",
            "full_name": None,
            "is_active": True,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

    # Override dependency to inject a fixed user id
    # Use FastAPI dependency_overrides to bypass auth and return our fixed user_id
    from src.notemesh.main import app
    from src.notemesh.api.auth import get_current_user_id as real_dep
    app.dependency_overrides[real_dep] = lambda: str(user_id)

    from src.notemesh.core.services.auth_service import AuthService
    monkeypatch.setattr(AuthService, "get_current_user", fake_get_current_user, raising=True)

    resp = client.get("/api/auth/me")
    from src.notemesh.main import app
    # cleanup override
    app.dependency_overrides.pop(real_dep, None)
    data = _json_ok(resp)
    assert data["id"] == str(user_id)


def test_update_profile_calls_service(monkeypatch, client):
    user_id = uuid.uuid4()

    async def fake_update(self, uid, req):
        assert str(uid) == str(user_id)
        return {
            "id": str(uid),
            "username": req.username or "bob",
            "full_name": req.full_name,
            "is_active": True,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }

    from src.notemesh.main import app
    from src.notemesh.api.auth import get_current_user_id as real_dep
    app.dependency_overrides[real_dep] = lambda: str(user_id)

    from src.notemesh.core.services.auth_service import AuthService
    monkeypatch.setattr(AuthService, "update_user_profile", fake_update, raising=True)

    resp = client.put("/api/auth/me", json={"username": "alice"})
    # cleanup override
    app.dependency_overrides.pop(real_dep, None)
    data = _json_ok(resp)
    assert data["username"] == "alice"


def test_change_password_calls_service(monkeypatch, client):
    user_id = uuid.uuid4()

    async def fake_change(self, uid, req):
        assert str(uid) == str(user_id)
        return True

    from src.notemesh.main import app
    from src.notemesh.api.auth import get_current_user_id as real_dep
    app.dependency_overrides[real_dep] = lambda: str(user_id)

    from src.notemesh.core.services.auth_service import AuthService
    monkeypatch.setattr(AuthService, "change_password", fake_change, raising=True)

    payload = {
        "current_password": "OldPass123!",
        "new_password": "NewPass123!",
        "confirm_new_password": "NewPass123!",
    }
    resp = client.post("/api/auth/change-password", json=payload)
    # cleanup override
    app.dependency_overrides.pop(real_dep, None)
    data = _json_ok(resp)
    assert data["message"] == "Password changed successfully"


def test_logout_calls_service(monkeypatch, client):
    user_id = uuid.uuid4()

    async def fake_logout(self, uid, token):
        assert str(uid) == str(user_id)
        return True

    from src.notemesh.main import app
    from src.notemesh.api.auth import get_current_user_id as real_dep
    app.dependency_overrides[real_dep] = lambda: str(user_id)

    from src.notemesh.core.services.auth_service import AuthService
    monkeypatch.setattr(AuthService, "logout_user", fake_logout, raising=True)

    resp = client.post("/api/auth/logout")
    # cleanup override
    app.dependency_overrides.pop(real_dep, None)
    data = _json_ok(resp)
    assert data["message"] == "Logged out successfully"
