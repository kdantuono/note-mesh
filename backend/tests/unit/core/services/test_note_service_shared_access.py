"""Unit tests for NoteService.get_note shared-access behavior."""

import uuid
from datetime import datetime, timezone
import pytest

from fastapi import HTTPException

from src.notemesh.core.services.note_service import NoteService


class DummyNote:
    def __init__(self, id: uuid.UUID, owner_id: uuid.UUID, title: str = "t", content: str = "c"):
        self.id = id
        self.owner_id = owner_id
        self.title = title
        self.content = content
        self.tags = []
        self.hyperlinks = []
        # Provide required timestamps for NoteResponse validation
        now = datetime.now(timezone.utc)
        self.created_at = now
        self.updated_at = now


@pytest.mark.asyncio
async def test_get_note_owned(monkeypatch):
    session = object()
    svc = NoteService(session)  # type: ignore[arg-type]

    owner_id = uuid.uuid4()
    note_id = uuid.uuid4()
    note = DummyNote(note_id, owner_id)

    async def fake_get_by_id_and_user(self, nid, uid):
        assert nid == note_id and uid == owner_id
        return note

    async def fake_check_access(self, nid, uid):
        raise AssertionError("should not be called when owned")

    async def fake_get_user_info(self, user_id):
        # Mock user for owner
        from unittest.mock import Mock
        from src.notemesh.core.models.user import User
        user = Mock(spec=User)
        user.id = user_id
        user.username = "testuser"
        user.full_name = "Test User"
        return user

    monkeypatch.setattr(
        svc.note_repo,
        "get_by_id_and_user",
        fake_get_by_id_and_user.__get__(svc.note_repo, type(svc.note_repo)),
    )
    monkeypatch.setattr(
        svc.share_repo,
        "check_note_access",
        fake_check_access.__get__(svc.share_repo, type(svc.share_repo)),
    )
    monkeypatch.setattr(
        svc.user_repo,
        "get_by_id",
        fake_get_user_info.__get__(svc.user_repo, type(svc.user_repo)),
    )

    res = await svc.get_note(note_id, owner_id)
    assert str(res.id) == str(note_id)
    assert res.is_shared is False
    assert res.can_edit is True


@pytest.mark.asyncio
async def test_get_note_shared_read_access(monkeypatch):
    session = object()
    svc = NoteService(session)  # type: ignore[arg-type]

    owner_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    note_id = uuid.uuid4()
    note = DummyNote(note_id, owner_id)

    async def fake_get_by_id_and_user(self, nid, uid):
        return None  # not owned by other_user

    async def fake_check_access(self, nid, uid):
        assert nid == note_id and uid == other_user_id
        return {"can_read": True, "can_write": False}

    async def fake_get_by_id(self, nid):
        assert nid == note_id
        return note

    async def fake_get_user_info(self, user_id):
        # Mock user for owner
        from unittest.mock import Mock
        from src.notemesh.core.models.user import User
        user = Mock(spec=User)
        user.id = user_id
        user.username = "testuser"
        user.full_name = "Test User"
        return user

    monkeypatch.setattr(
        svc.note_repo,
        "get_by_id_and_user",
        fake_get_by_id_and_user.__get__(svc.note_repo, type(svc.note_repo)),
    )
    monkeypatch.setattr(
        svc.share_repo,
        "check_note_access",
        fake_check_access.__get__(svc.share_repo, type(svc.share_repo)),
    )
    monkeypatch.setattr(
        svc.note_repo, "get_by_id", fake_get_by_id.__get__(svc.note_repo, type(svc.note_repo))
    )
    monkeypatch.setattr(
        svc.user_repo,
        "get_by_id",
        fake_get_user_info.__get__(svc.user_repo, type(svc.user_repo)),
    )

    res = await svc.get_note(note_id, other_user_id)
    assert str(res.id) == str(note_id)
    assert res.is_shared is True
    assert res.can_edit is False


@pytest.mark.asyncio
async def test_get_note_no_access_returns_404(monkeypatch):
    session = object()
    svc = NoteService(session)  # type: ignore[arg-type]

    user_id = uuid.uuid4()
    note_id = uuid.uuid4()

    async def fake_get_by_id_and_user(self, nid, uid):
        return None

    async def fake_check_access(self, nid, uid):
        return {"can_read": False}

    monkeypatch.setattr(
        svc.note_repo,
        "get_by_id_and_user",
        fake_get_by_id_and_user.__get__(svc.note_repo, type(svc.note_repo)),
    )
    monkeypatch.setattr(
        svc.share_repo,
        "check_note_access",
        fake_check_access.__get__(svc.share_repo, type(svc.share_repo)),
    )

    with pytest.raises(HTTPException) as exc:
        await svc.get_note(note_id, user_id)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Note not found"
