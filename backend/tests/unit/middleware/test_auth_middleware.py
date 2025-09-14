"""Unit tests for middleware auth (src/notemesh/middleware/auth.py)."""

import uuid
from typing import Optional

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.notemesh.middleware.auth import JWTBearer, get_current_user_id


def build_app(depends_current_user: bool = False) -> FastAPI:
    app = FastAPI()

    @app.get("/protected")
    async def protected(user_id=Depends(JWTBearer())):
        return {"user_id": str(user_id)}

    @app.get("/me")
    async def me(
        user_id=Depends(get_current_user_id) if depends_current_user else Depends(JWTBearer()),
    ):
        return {"user_id": str(user_id)}

    return app


def _make_bearer(token: Optional[str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token is not None else {}


def test_jwtbearer_accepts_valid_token(monkeypatch):
    # Monkeypatch token decoder to return a fixed user id
    uid = uuid.uuid4()
    from src.notemesh.middleware import auth as auth_module

    monkeypatch.setattr(auth_module, "get_user_id_from_token", lambda t: uid)

    app = build_app()
    client = TestClient(app)
    resp = client.get("/protected", headers=_make_bearer("valid-token"))
    assert resp.status_code == 200
    assert resp.json() == {"user_id": str(uid)}


def test_jwtbearer_rejects_missing_header():
    app = build_app()
    client = TestClient(app)
    resp = client.get("/protected")
    assert resp.status_code == 403


def test_jwtbearer_rejects_wrong_scheme():
    app = build_app()
    client = TestClient(app)
    resp = client.get("/protected", headers={"Authorization": "Basic abc"})
    assert resp.status_code == 403


def test_jwtbearer_rejects_invalid_token(monkeypatch):
    from src.notemesh import security as security_pkg

    monkeypatch.setattr(security_pkg, "get_user_id_from_token", lambda t: None)

    app = build_app()
    client = TestClient(app)
    resp = client.get("/protected", headers=_make_bearer("invalid"))
    assert resp.status_code == 403


def test_get_current_user_id_dependency(monkeypatch):
    uid = uuid.uuid4()
    from src.notemesh.middleware import auth as auth_module

    monkeypatch.setattr(auth_module, "get_user_id_from_token", lambda t: uid)

    app = build_app(depends_current_user=True)
    client = TestClient(app)
    resp = client.get("/me", headers=_make_bearer("valid"))
    assert resp.status_code == 200
    assert resp.json() == {"user_id": str(uid)}
