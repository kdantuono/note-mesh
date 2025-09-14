import uuid
import pytest
import sys
from datetime import datetime

from src.notemesh.core.services.note_service import NoteService


class Dummy:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeNoteRepo:
    def __init__(self, note):
        self.note = note
        self.updated = None
        self.deleted = False
        self.listed = ([note], 1)
        self.tags = ["work", "home"]
    async def create_note(self, data):
        return self.note
    async def get_by_id_and_user(self, nid, uid):
        return self.note if self.note and self.note.id == nid and self.note.owner_id == uid else None
    async def update_note(self, nid, uid, upd):
        self.updated = upd
        return self.note
    async def delete_note(self, nid, uid):
        self.deleted = True
        return True
    async def list_user_notes(self, uid, page, per_page, tag_filter):
        return self.listed
    async def get_user_tags(self, uid):
        return self.tags


class FakeSession:
    def __init__(self):
        self.executed = []
        self.added = []
        self.committed = 0
    async def execute(self, stmt):
        self.executed.append(stmt)
        class R:
            def __init__(self, val=None):
                self._val = val
            def scalar_one_or_none(self):
                return None
        return R()
    def add(self, obj):
        self.added.append(obj)
    async def flush(self):
        pass
    async def commit(self):
        self.committed += 1
    async def refresh(self, obj, attrs=None):
        pass


@pytest.mark.asyncio
async def test_create_and_get_update_delete_and_list(monkeypatch):
    user_id = uuid.uuid4()
    note_id = uuid.uuid4()
    now = datetime.utcnow()
    note = Dummy(
        id=note_id,
        owner_id=user_id,
        title="T",
        content="c #work",
        tags=[],
        hyperlinks=[],
        created_at=now,
        updated_at=now,
    )

    import src.notemesh.core.services.note_service as ns
    repo = FakeNoteRepo(note)
    monkeypatch.setattr(ns, "NoteRepository", lambda s: repo, raising=True)
    svc = NoteService(session=FakeSession())

    # create accumulates tags from content
    created = await svc.create_note(user_id, Dummy(title="T", content="c #work", is_public=False, hyperlinks=[], tags=["home"]))
    assert set(created.tags) == {"work", "home"}

    # get
    got = await svc.get_note(note_id, user_id)
    assert got.id == note_id

    # update
    upd = await svc.update_note(note_id, user_id, Dummy(title="T2", content="new #x", is_public=True, hyperlinks=["http://a"], tags=["y"]))
    assert repo.updated["title"] == "T2"

    # delete
    ok = await svc.delete_note(note_id, user_id)
    assert ok is True and repo.deleted is True

    # list
    lst = await svc.list_user_notes(user_id, page=1, per_page=10, tag_filter=None)
    assert lst.total == 1 and lst.items[0].id == note_id

    # tags
    tags = await svc.get_available_tags(user_id)
    assert tags == ["work", "home"]


@pytest.mark.asyncio
async def test_validate_hyperlinks(monkeypatch):
    svc = NoteService(session=FakeSession())

    class FakeResp:
        def __init__(self, status):
            self.status = status

    class FakeClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
        def get(self, url, timeout=5):
            class Ctx:
                def __init__(self, status): self.status = status
                async def __aenter__(self): return FakeResp(self.status)
                async def __aexit__(self, et, e, tb): return False
            if "good" in url:
                return Ctx(200)
            raise RuntimeError("bad url")

    import types
    fake_aiohttp = types.SimpleNamespace(ClientSession=FakeClient)
    sys.modules['aiohttp'] = fake_aiohttp

    res = await svc.validate_hyperlinks(["http://good.example", "bad://nope"])
    assert res["http://good.example"] is True
    assert res["bad://nope"] is False
