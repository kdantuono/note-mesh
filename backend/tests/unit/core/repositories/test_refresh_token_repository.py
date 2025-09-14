"""Unit tests for RefreshTokenRepository without DB."""

from datetime import datetime, timedelta, timezone
import uuid
import pytest

from src.notemesh.core.repositories.refresh_token_repository import RefreshTokenRepository


class DummyToken:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeResult:
    def __init__(self, scalar=None, rowcount=0):
        self._scalar = scalar
        self._rowcount = rowcount

    def scalar_one_or_none(self):
        return self._scalar

    @property
    def rowcount(self):
        return self._rowcount


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
async def test_create_get_delete_token_and_validity():
    uid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    token_obj = DummyToken(user_id=uid, token="abc", expires_at=now + timedelta(hours=1), is_active=True)

    # create
    create_session = FakeSession()
    repo = RefreshTokenRepository(create_session)
    created = await repo.create_token({"user_id": uid, "token": "abc", "expires_at": token_obj.expires_at, "is_active": True})
    assert create_session.added and create_session.commits == 1 and created is not None

    # get_by_token and is_token_valid
    get_session = FakeSession(FakeResult(token_obj))
    repo2 = RefreshTokenRepository(get_session)
    got = await repo2.get_by_token("abc")
    assert got is token_obj
    assert await repo2.is_token_valid("abc") is True

    # expired -> invalid
    expired_token = DummyToken(user_id=uid, token="old", expires_at=now - timedelta(seconds=1), is_active=True)
    repo3 = RefreshTokenRepository(FakeSession(FakeResult(expired_token)))
    assert await repo3.is_token_valid("old") is False

    # delete_token true/false
    del_true = await repo2.delete_token("abc")
    assert del_true is True
    assert get_session.deleted and get_session.commits == 1

    repo_none = RefreshTokenRepository(FakeSession(FakeResult(None)))
    del_false = await repo_none.delete_token("missing")
    assert del_false is False


@pytest.mark.asyncio
async def test_delete_user_and_expired_tokens_counts():
    session1 = FakeSession(FakeResult(rowcount=3))
    repo1 = RefreshTokenRepository(session1)
    cnt1 = await repo1.delete_user_tokens(uuid.uuid4())
    assert cnt1 == 3 and session1.commits == 1

    session2 = FakeSession(FakeResult(rowcount=2))
    repo2 = RefreshTokenRepository(session2)
    cnt2 = await repo2.delete_expired_tokens()
    assert cnt2 == 2 and session2.commits == 1
