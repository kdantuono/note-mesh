"""Unit tests for ShareRepository without a real DB."""

import uuid
import pytest

from src.notemesh.core.repositories.share_repository import ShareRepository


class Dummy:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeScalarResult:
    def __init__(self, scalar=None, scalars_list=None):
        self._scalar = scalar
        self._scalars_list = scalars_list or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalar(self):
        return self._scalar

    def scalars(self):
        class _It:
            def __init__(self, data):
                self._data = data
            def all(self):
                return self._data
            def __iter__(self):
                return iter(self._data)
            def __len__(self):
                return len(self._data)
            def __getitem__(self, idx):
                return self._data[idx]
        return _It(self._scalars_list)


class FakeSession:
    def __init__(self, results_iter):
        self._results = list(results_iter)
        self.added = []
        self.deleted = []
        self.commits = 0
        self.refreshed = []

    async def execute(self, stmt):
        return self._results.pop(0) if self._results else FakeScalarResult(None)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj, attrs=None):
        self.refreshed.append((obj, attrs))

    async def delete(self, obj):
        self.deleted.append(obj)


@pytest.mark.asyncio
async def test_create_get_list_and_revoke_share():
    owner = uuid.uuid4()
    note_id = uuid.uuid4()
    share_id = uuid.uuid4()
    share_obj = Dummy(id=share_id, note_id=note_id, owner_id=owner, shared_with=uuid.uuid4())

    # create_share -> commit+refresh
    session = FakeSession(results_iter=[])
    repo = ShareRepository(session)
    created = await repo.create_share({
        "id": share_id,
        "note_id": note_id,
        "shared_by_user_id": owner,
        "shared_with_user_id": share_obj.shared_with,
    })
    assert session.added and session.commits == 1 and session.refreshed

    # get_by_id -> returns the dummy when present
    session2 = FakeSession(results_iter=[FakeScalarResult(share_obj)])
    repo2 = ShareRepository(session2)
    got = await repo2.get_by_id(share_id)
    assert got is share_obj

    # list_shares_given -> returns scalars list and count
    s3 = FakeSession(results_iter=[FakeScalarResult(1), FakeScalarResult(scalars_list=[share_obj])])
    repo3 = ShareRepository(s3)
    lst, total = await repo3.list_shares_given(owner, page=1, per_page=10)
    assert total == 1 and lst == [share_obj]

    # revoke_share true/false
    s4 = FakeSession(results_iter=[FakeScalarResult(share_obj)])
    repo4 = ShareRepository(s4)
    ok = await repo4.delete_share(share_id, owner)
    assert ok is True and s4.deleted

    s5 = FakeSession(results_iter=[FakeScalarResult(None)])
    repo5 = ShareRepository(s5)
    nok = await repo5.delete_share(share_id, owner)
    assert nok is False
