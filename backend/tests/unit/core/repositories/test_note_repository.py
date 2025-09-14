"""Unit tests for NoteRepository without DB."""

import uuid
import pytest

from src.notemesh.core.repositories.note_repository import NoteRepository


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
        return _It(self._scalars_list)


class FakeSession:
    def __init__(self, results_iter):
        self._results = list(results_iter)
        self.added = []
        self.deleted = []
        self.commits = 0
        self.refreshed = []

    async def execute(self, stmt):
        # Return next preset result
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
async def test_create_get_update_delete_note_flow():
    owner = uuid.uuid4()
    note_id = uuid.uuid4()
    dummy_note = Dummy(id=note_id, owner_id=owner, title="t", content="c", tags=[], updated_at=None, created_at=None, hyperlinks=None)

    # create -> commit+refresh, then get_by_id returns our dummy
    session = FakeSession(results_iter=[FakeScalarResult(dummy_note)])
    repo = NoteRepository(session)
    created = await repo.create_note({"id": note_id, "owner_id": owner, "title": "t", "content": "c", "is_public": False, "hyperlinks": []})
    assert session.added and session.commits == 1 and session.refreshed

    got = await repo.get_by_id(note_id)
    assert got is dummy_note

    # get_by_id_and_user ok and then update_note returns same dummy after commit/refresh
    # One result for explicit get_by_id_and_user call, another for update_note's internal fetch
    session2 = FakeSession(results_iter=[FakeScalarResult(dummy_note), FakeScalarResult(dummy_note)])
    repo2 = NoteRepository(session2)
    ok = await repo2.get_by_id_and_user(note_id, owner)
    assert ok is dummy_note
    updated = await repo2.update_note(note_id, owner, {"title": "t2"})
    assert updated is dummy_note
    assert session2.commits == 1

    # delete_note true false
    session3 = FakeSession(results_iter=[FakeScalarResult(dummy_note)])
    repo3 = NoteRepository(session3)
    deleted_ok = await repo3.delete_note(note_id, owner)
    assert deleted_ok is True and session3.deleted

    session4 = FakeSession(results_iter=[FakeScalarResult(None)])
    repo4 = NoteRepository(session4)
    deleted_false = await repo4.delete_note(note_id, owner)
    assert deleted_false is False


@pytest.mark.asyncio
async def test_list_user_notes_and_tags_and_search():
    owner = uuid.uuid4()
    n1 = Dummy(id=uuid.uuid4(), owner_id=owner, title="a", content="x", tags=[], updated_at=1, created_at=None)
    n2 = Dummy(id=uuid.uuid4(), owner_id=owner, title="b", content="y", tags=[], updated_at=2, created_at=None)
    # list_user_notes expects two executes: count then data
    session = FakeSession(results_iter=[FakeScalarResult(2), FakeScalarResult(scalars_list=[n1, n2])])
    repo = NoteRepository(session)
    notes, total = await repo.list_user_notes(owner, page=1, per_page=20, tag_filter=None)
    assert total == 2 and len(notes) == 2

    # get_user_tags returns list of names from scalars
    session2 = FakeSession(results_iter=[FakeScalarResult(scalars_list=["work", "home"])])
    repo2 = NoteRepository(session2)
    tags = await repo2.get_user_tags(owner)
    assert tags == ["work", "home"]

    # search_notes returns scalars list
    session3 = FakeSession(results_iter=[FakeScalarResult(scalars_list=[n1, n2])])
    repo3 = NoteRepository(session3)
    res = await repo3.search_notes(owner, query="a", tag_filter=None)
    assert res == [n1, n2]
