import uuid
from datetime import datetime

import pytest
from fastapi import HTTPException

from src.notemesh.core.services.sharing_service import SharingService


class Dummy:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeShareRepo:
    def __init__(self):
        self.created = []
        self.deleted = []
        self.access = {}

    async def create_share(self, data):
        s = Dummy(
            id=uuid.uuid4(),
            note_id=data["note_id"],
            note=Dummy(title="T"),
            shared_with_user=Dummy(
                id=data.get("shared_with_user_id", uuid.uuid4()), username="u", full_name="U"
            ),
            permission=data.get("permission", "read"),
            share_message=data.get("share_message"),
            created_at=datetime.utcnow(),
            expires_at=None,
            last_accessed_at=None,
            is_active=True,
            access_count=0,
        )
        self.created.append(data)
        return s

    async def delete_share(self, share_id, user_id):
        self.deleted.append((share_id, user_id))
        return True

    async def check_note_access(self, note_id, user_id):
        return self.access.get(
            (note_id, user_id), {"can_read": True, "can_write": False, "can_share": False}
        )

    async def list_shares_given(self, user_id, page, per_page):
        return [], 0

    async def list_shares_received(self, user_id, page, per_page):
        return [], 0

    async def get_share_stats(self, user_id):
        return {"shares_given": 1, "shares_received": 2, "unique_notes_shared": 1}

    async def get_existing_share(self, note_id, shared_with_user_id):
        # For testing, return None (no existing share)
        return None

    async def update_share(self, share_id, update_data):
        # For testing, return a dummy updated share
        return Dummy(
            id=share_id,
            note_id=uuid.uuid4(),
            note=Dummy(title="T"),
            shared_with_user=Dummy(id=uuid.uuid4(), username="u", full_name="U"),
            permission=update_data.get("permission", "read"),
            share_message=update_data.get("share_message"),
            created_at=datetime.utcnow(),
            expires_at=None,
            last_accessed_at=None,
            is_active=True,
            access_count=0,
        )


class FakeUserRepo:
    def __init__(self, users_by_name):
        self.users_by_name = users_by_name

    async def get_by_username(self, username):
        return self.users_by_name.get(username)

    async def get_by_id(self, uid):
        return Dummy(username="owner", full_name="Owner")


class FakeNoteRepo:
    def __init__(self, notes):
        self.notes = notes

    async def get_by_id_and_user(self, nid, uid):
        return self.notes.get((nid, uid))

    async def get_by_id(self, nid):
        return self.notes.get(nid)


@pytest.mark.asyncio
async def test_share_note_happy_path(monkeypatch):
    user_id = uuid.uuid4()
    note_id = uuid.uuid4()
    fake_share = FakeShareRepo()
    fake_users = FakeUserRepo({"alice": Dummy(id=uuid.uuid4(), username="alice")})
    fake_notes = FakeNoteRepo(
        {(note_id, user_id): Dummy(id=note_id, owner_id=user_id, title="N", tags=[])}
    )

    import src.notemesh.core.services.sharing_service as sh

    monkeypatch.setattr(sh, "ShareRepository", lambda s: fake_share, raising=True)
    monkeypatch.setattr(sh, "UserRepository", lambda s: fake_users, raising=True)
    monkeypatch.setattr(sh, "NoteRepository", lambda s: fake_notes, raising=True)
    svc = SharingService(session=None)

    req = Dummy(
        note_id=note_id, shared_with_usernames=["alice"], permission_level="read", message="hi", expires_at=None
    )
    out = await svc.share_note(user_id, req)
    assert len(out) == 1
    assert fake_share.created and fake_share.created[0]["note_id"] == note_id


@pytest.mark.asyncio
async def test_share_note_user_not_found(monkeypatch):
    user_id = uuid.uuid4()
    note_id = uuid.uuid4()
    fake_share = FakeShareRepo()
    fake_users = FakeUserRepo({})
    fake_notes = FakeNoteRepo(
        {(note_id, user_id): Dummy(id=note_id, owner_id=user_id, title="N", tags=[])}
    )

    import src.notemesh.core.services.sharing_service as sh

    monkeypatch.setattr(sh, "ShareRepository", lambda s: fake_share, raising=True)
    monkeypatch.setattr(sh, "UserRepository", lambda s: fake_users, raising=True)
    monkeypatch.setattr(sh, "NoteRepository", lambda s: fake_notes, raising=True)
    svc = SharingService(session=None)

    req = Dummy(
        note_id=note_id, shared_with_usernames=["ghost"], permission_level="read", message="hi", expires_at=None
    )
    with pytest.raises(HTTPException) as ei:
        await svc.share_note(user_id, req)
    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_get_shared_note_permissions_and_owner(monkeypatch):
    user_id = uuid.uuid4()
    note_id = uuid.uuid4()
    fake_share = FakeShareRepo()
    fake_share.access[(note_id, user_id)] = {"can_read": True, "can_write": True, "can_share": True}
    fake_users = FakeUserRepo({})
    from datetime import datetime

    now = datetime.utcnow()
    fake_notes = FakeNoteRepo(
        {
            note_id: Dummy(
                id=note_id,
                owner_id=uuid.uuid4(),
                title="N",
                content="c",
                tags=[],
                created_at=now,
                updated_at=now,
                hyperlinks=[],
            )
        }
    )

    import src.notemesh.core.services.sharing_service as sh

    monkeypatch.setattr(sh, "ShareRepository", lambda s: fake_share, raising=True)
    monkeypatch.setattr(sh, "UserRepository", lambda s: fake_users, raising=True)
    monkeypatch.setattr(sh, "NoteRepository", lambda s: fake_notes, raising=True)
    svc = SharingService(session=None)

    res = await svc.get_shared_note(note_id, user_id)
    assert res.id == note_id and res.can_write is True and res.can_share is True


@pytest.mark.asyncio
async def test_get_shared_note_forbidden(monkeypatch):
    user_id = uuid.uuid4()
    note_id = uuid.uuid4()
    fake_share = FakeShareRepo()
    fake_share.access[(note_id, user_id)] = {
        "can_read": False,
        "can_write": False,
        "can_share": False,
    }
    fake_users = FakeUserRepo({})
    fake_notes = FakeNoteRepo({})

    import src.notemesh.core.services.sharing_service as sh

    monkeypatch.setattr(sh, "ShareRepository", lambda s: fake_share, raising=True)
    monkeypatch.setattr(sh, "UserRepository", lambda s: fake_users, raising=True)
    monkeypatch.setattr(sh, "NoteRepository", lambda s: fake_notes, raising=True)
    svc = SharingService(session=None)

    with pytest.raises(HTTPException) as ei:
        await svc.get_shared_note(note_id, user_id)
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_list_and_stats(monkeypatch):
    user_id = uuid.uuid4()
    fake_share = FakeShareRepo()
    fake_users = FakeUserRepo({})
    fake_notes = FakeNoteRepo({})

    import src.notemesh.core.services.sharing_service as sh

    monkeypatch.setattr(sh, "ShareRepository", lambda s: fake_share, raising=True)
    monkeypatch.setattr(sh, "UserRepository", lambda s: fake_users, raising=True)
    monkeypatch.setattr(sh, "NoteRepository", lambda s: fake_notes, raising=True)
    svc = SharingService(session=None)

    # list shares given default
    req = Dummy(page=1, per_page=10, type="given")
    res = await svc.list_shares(user_id, req)
    assert res.total_count == 0 and res.page == 1 and res.per_page == 10

    # stats
    stats = await svc.get_share_stats(user_id)
    assert stats.shares_given == 1 and stats.shares_received == 2
