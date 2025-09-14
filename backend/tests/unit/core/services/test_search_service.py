import uuid
import pytest

from src.notemesh.core.services.search_service import SearchService
from src.notemesh.core.schemas.notes import NoteSearchRequest
from datetime import datetime


class Dummy:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeNoteRepo:
    def __init__(self):
        self.tags = ["work", "home", "python"]
        now = datetime.utcnow()
        self.notes = [
            Dummy(
                id=uuid.uuid4(),
                owner_id=uuid.uuid4(),
                title="T",
                content="c",
                tags=[],
                created_at=now,
                updated_at=now,
            )
        ]
    async def search_notes(self, user_id=None, query=None, tag_filter=None):
        return self.notes
    async def get_user_tags(self, uid):
        return self.tags


@pytest.mark.asyncio
async def test_search_and_suggestions(monkeypatch):
    import src.notemesh.core.services.search_service as ss
    repo = FakeNoteRepo()
    monkeypatch.setattr(ss, "NoteRepository", lambda s: repo, raising=True)

    svc = SearchService(session=None)

    user_id = uuid.uuid4()
    req = NoteSearchRequest(query="T", tags=None)
    res = await svc.search_notes(user_id, req)
    assert res.items and res.total == 1 and res.items[0].title == "T"

    sugg = await svc.suggest_tags(user_id, query="p")
    assert "python" in sugg
