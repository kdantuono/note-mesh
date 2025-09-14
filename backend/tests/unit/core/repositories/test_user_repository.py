"""Unit tests for UserRepository without DB."""

import uuid
import pytest

from src.notemesh.core.repositories.user_repository import UserRepository
from src.notemesh.core.models.user import User


class FakeResult:
    def __init__(self, scalar=None):
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._scalar


class FakeSession:
    def __init__(self, result=None):
        self._result = result
        self.added = []
        self.deleted = []
        self.commits = 0
        self.refreshed = []

    async def execute(self, stmt):
        return self._result

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj, attrs=None):
        self.refreshed.append((obj, attrs))

    async def delete(self, obj):
        self.deleted.append(obj)


@pytest.mark.asyncio
async def test_create_user():
    session = FakeSession()
    repo = UserRepository(session)
    data = {"username": "alice", "password_hash": "h", "is_active": True, "is_verified": True}
    user = await repo.create_user(data)
    assert isinstance(user, User)
    assert session.added and isinstance(session.added[0], User)
    assert session.commits == 1
    assert session.refreshed and session.refreshed[0][0] is user


@pytest.mark.asyncio
async def test_get_by_id_found_and_not_found():
    uid = uuid.uuid4()
    session = FakeSession(FakeResult(User(id=uid, username="bob", password_hash="x", is_active=True, is_verified=True)))
    repo = UserRepository(session)
    u = await repo.get_by_id(uid)
    assert isinstance(u, User)

    session_none = FakeSession(FakeResult(None))
    repo_none = UserRepository(session_none)
    u2 = await repo_none.get_by_id(uid)
    assert u2 is None


@pytest.mark.asyncio
async def test_get_by_username_found_and_not_found():
    session = FakeSession(FakeResult(User(id=uuid.uuid4(), username="charlie", password_hash="x", is_active=True, is_verified=True)))
    repo = UserRepository(session)
    u = await repo.get_by_username("charlie")
    assert isinstance(u, User)

    session_none = FakeSession(FakeResult(None))
    repo_none = UserRepository(session_none)
    u2 = await repo_none.get_by_username("missing")
    assert u2 is None


@pytest.mark.asyncio
async def test_update_user_updates_fields_and_commits(monkeypatch):
    uid = uuid.uuid4()
    user_obj = User(id=uid, username="dave", password_hash="x", is_active=True, is_verified=True)
    session = FakeSession(FakeResult(user_obj))
    repo = UserRepository(session)
    updated = await repo.update_user(uid, {"full_name": "Dave"})
    assert updated.full_name == "Dave"
    assert session.commits == 1
    assert session.refreshed and session.refreshed[0][0] is updated

    # Not found path
    repo_none = UserRepository(FakeSession(FakeResult(None)))
    updated_none = await repo_none.update_user(uid, {"username": "new"})
    assert updated_none is None


@pytest.mark.asyncio
async def test_delete_user_true_false():
    uid = uuid.uuid4()
    user_obj = User(id=uid, username="eve", password_hash="x", is_active=True, is_verified=True)
    session = FakeSession(FakeResult(user_obj))
    repo = UserRepository(session)
    ok = await repo.delete_user(uid)
    assert ok is True
    assert session.deleted and session.deleted[0] is user_obj
    assert session.commits == 1

    repo_none = UserRepository(FakeSession(FakeResult(None)))
    ok2 = await repo_none.delete_user(uid)
    assert ok2 is False


@pytest.mark.asyncio
async def test_is_username_taken():
    session = FakeSession(FakeResult(User(id=uuid.uuid4(), username="zoe", password_hash="x", is_active=True, is_verified=True)))
    repo = UserRepository(session)
    assert await repo.is_username_taken("zoe") is True

    repo_none = UserRepository(FakeSession(FakeResult(None)))
    assert await repo_none.is_username_taken("nobody") is False
