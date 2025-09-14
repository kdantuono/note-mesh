"""
Unit tests for Note model.
"""

import uuid
from datetime import datetime

import pytest

from src.notemesh.core.models.note import Note
from src.notemesh.core.models.share import Share
from src.notemesh.core.models.tag import Tag
from src.notemesh.core.models.user import User


class TestNoteModel:
    """Test Note model functionality."""

    @pytest.mark.asyncio
    async def test_create_note(self, test_session, test_user):
        """Test creating a note."""
        note = Note(
            title="Test Note",
            content="This is test content",
            is_public=False,
            owner_id=test_user.id,
        )

        test_session.add(note)
        await test_session.commit()
        await test_session.refresh(note)

        assert note.id is not None
        assert isinstance(note.id, uuid.UUID)
        assert note.title == "Test Note"
        assert note.content == "This is test content"
        assert note.is_public is False
        assert note.owner_id == test_user.id
        assert note.view_count == 0
        assert note.last_viewed_at is None
        assert note.hyperlinks is None

    @pytest.mark.asyncio
    async def test_note_with_hyperlinks(self, test_session, test_user):
        """Test note with hyperlinks."""
        links = ["https://example.com", "https://test.org/page", "http://localhost:3000"]

        note = Note(
            title="Note with Links",
            content="Content with links",
            hyperlinks=links,
            owner_id=test_user.id,
        )

        test_session.add(note)
        await test_session.commit()
        await test_session.refresh(note)

        assert note.hyperlinks == links
        assert note.hyperlink_count == 3

    @pytest.mark.asyncio
    async def test_note_repr(self, test_session, test_user):
        """Test note string representation."""
        note = Note(
            title="A very long title that should be truncated in the representation",
            content="Content",
            owner_id=test_user.id,
        )

        test_session.add(note)
        await test_session.commit()

        expected = f"<Note(title='A very long title that should ...', owner_id={test_user.id})>"
        assert repr(note) == expected

    @pytest.mark.asyncio
    async def test_note_preview_short_content(self, test_session, test_user):
        """Test preview property with short content."""
        note = Note(title="Short Note", content="Short content", owner_id=test_user.id)

        test_session.add(note)
        await test_session.commit()

        assert note.preview == "Short content"

    @pytest.mark.asyncio
    async def test_note_preview_long_content(self, test_session, test_user):
        """Test preview property with long content."""
        long_content = "a" * 200  # 200 characters

        note = Note(title="Long Note", content=long_content, owner_id=test_user.id)

        test_session.add(note)
        await test_session.commit()

        assert note.preview == "a" * 147 + "..."
        assert len(note.preview) == 150

    @pytest.mark.asyncio
    async def test_note_hyperlink_count_empty(self, test_session, test_user):
        """Test hyperlink_count with no hyperlinks."""
        note = Note(title="No Links", content="Content without links", owner_id=test_user.id)

        test_session.add(note)
        await test_session.commit()

        assert note.hyperlink_count == 0

    @pytest.mark.asyncio
    async def test_note_owner_relationship(self, test_session, test_user):
        """Test note-owner relationship."""
        note = Note(title="Owner Test", content="Content", owner_id=test_user.id)

        test_session.add(note)
        await test_session.commit()
        await test_session.refresh(note)

        assert note.owner == test_user
        assert note.owner.username == test_user.username

    @pytest.mark.asyncio
    async def test_note_tags_relationship(self, test_session, test_user):
        """Test note-tags many-to-many relationship."""
        note = Note(title="Tagged Note", content="Content", owner_id=test_user.id)

        tag1 = Tag(name="python", description="Python related")
        tag2 = Tag(name="testing", description="Testing related")

        test_session.add_all([note, tag1, tag2])
        await test_session.commit()

        # Add tags to note
        note.tags.append(tag1)
        note.tags.append(tag2)
        await test_session.commit()
        await test_session.refresh(note)

        assert len(note.tags) == 2
        assert tag1 in note.tags
        assert tag2 in note.tags

    @pytest.mark.asyncio
    async def test_note_shares_relationship(self, test_session, test_user):
        """Test note-shares relationship."""
        # Create another user to share with
        other_user = User(username="otheruser", password_hash="hash")
        test_session.add(other_user)

        note = Note(title="Shared Note", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        await test_session.refresh(note)
        await test_session.refresh(other_user)

        # Create share
        share = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=other_user.id,
            permission="read",
        )
        test_session.add(share)
        await test_session.commit()
        await test_session.refresh(note)

        assert len(note.shares) == 1
        assert share in note.shares

    @pytest.mark.asyncio
    async def test_note_cascade_delete_shares(self, test_session, test_user):
        """Test that deleting note cascades to shares."""
        other_user = User(username="otheruser2", password_hash="hash")
        test_session.add(other_user)

        note = Note(title="To Delete", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        await test_session.refresh(other_user)

        share = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=other_user.id,
            permission="read",
        )
        test_session.add(share)
        await test_session.commit()

        share_id = share.id

        # Delete note
        await test_session.delete(note)
        await test_session.commit()

        # Check share is deleted
        deleted_share = await test_session.get(Share, share_id)
        assert deleted_share is None

    @pytest.mark.asyncio
    async def test_note_public_flag(self, test_session, test_user):
        """Test public note flag."""
        public_note = Note(
            title="Public Note", content="Public content", is_public=True, owner_id=test_user.id
        )

        test_session.add(public_note)
        await test_session.commit()
        await test_session.refresh(public_note)

        assert public_note.is_public is True

    @pytest.mark.asyncio
    async def test_note_view_tracking(self, test_session, test_user):
        """Test view count and last viewed tracking."""
        note = Note(title="Viewed Note", content="Content", owner_id=test_user.id)

        test_session.add(note)
        await test_session.commit()

        # Update view tracking
        note.view_count = 5
        note.last_viewed_at = datetime.utcnow()
        await test_session.commit()
        await test_session.refresh(note)

        assert note.view_count == 5
        assert note.last_viewed_at is not None
        assert isinstance(note.last_viewed_at, datetime)

    @pytest.mark.asyncio
    async def test_note_field_constraints(self, test_session, test_user):
        """Test field constraints."""
        # Title too long (max 200)
        with pytest.raises(Exception):
            note = Note(title="a" * 201, content="Content", owner_id=test_user.id)  # Too long
            test_session.add(note)
            await test_session.commit()

        await test_session.rollback()

        # Hyperlink too long (max 500 per link)
        with pytest.raises(Exception):
            note = Note(
                title="Note",
                content="Content",
                hyperlinks=["https://" + "a" * 493],  # Too long (500+ chars)
                owner_id=test_user.id,
            )
            test_session.add(note)
            await test_session.commit()

    @pytest.mark.asyncio
    async def test_note_required_fields(self, test_session, test_user):
        """Test required fields."""
        # Missing title
        with pytest.raises(Exception):
            note = Note(content="Content", owner_id=test_user.id)
            test_session.add(note)
            await test_session.commit()

        await test_session.rollback()

        # Missing content
        with pytest.raises(Exception):
            note = Note(title="Title", owner_id=test_user.id)
            test_session.add(note)
            await test_session.commit()

        await test_session.rollback()

        # Missing owner_id
        with pytest.raises(Exception):
            note = Note(title="Title", content="Content")
            test_session.add(note)
            await test_session.commit()

    @pytest.mark.asyncio
    async def test_note_empty_hyperlinks(self, test_session, test_user):
        """Test note with empty hyperlinks array."""
        note = Note(title="Empty Links", content="Content", hyperlinks=[], owner_id=test_user.id)

        test_session.add(note)
        await test_session.commit()
        await test_session.refresh(note)

        assert note.hyperlinks == []
        assert note.hyperlink_count == 0
