"""
Unit tests for User model.
"""

import uuid
from datetime import datetime

import pytest

from src.notemesh.core.models.note import Note
from src.notemesh.core.models.refresh_token import RefreshToken
from src.notemesh.core.models.share import Share
from src.notemesh.core.models.user import User


class TestUserModel:
    """Test User model functionality."""

    @pytest.mark.asyncio
    async def test_create_user(self, test_session):
        """Test creating a user."""
        user = User(
            username="testuser",
            password_hash="hashed_password",
            full_name="Test User",
            is_active=True,
            is_verified=True,
        )

        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.username == "testuser"
        assert user.password_hash == "hashed_password"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_verified is True
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_user_defaults(self, test_session):
        """Test user default values."""
        user = User(username="minimal_user", password_hash="hashed")

        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        assert user.full_name is None
        assert user.is_active is True
        assert user.is_verified is True

    @pytest.mark.asyncio
    async def test_user_repr(self, test_session):
        """Test user string representation."""
        user = User(username="repruser", password_hash="hash")

        test_session.add(user)
        await test_session.commit()

        assert repr(user) == "<User(username='repruser')>"

    @pytest.mark.asyncio
    async def test_user_display_name_with_full_name(self, test_session):
        """Test display_name property when full_name is set."""
        user = User(username="testuser", password_hash="hash", full_name="John Doe")

        test_session.add(user)
        await test_session.commit()

        assert user.display_name == "John Doe"

    @pytest.mark.asyncio
    async def test_user_display_name_without_full_name(self, test_session):
        """Test display_name property when full_name is None."""
        user = User(username="testuser", password_hash="hash", full_name=None)

        test_session.add(user)
        await test_session.commit()

        assert user.display_name == "testuser"

    @pytest.mark.asyncio
    async def test_user_unique_username(self, test_session):
        """Test that username must be unique."""
        user1 = User(username="duplicate", password_hash="hash1")
        user2 = User(username="duplicate", password_hash="hash2")

        test_session.add(user1)
        await test_session.commit()

        test_session.add(user2)

        # Should raise integrity error on duplicate username
        with pytest.raises(Exception):  # IntegrityError
            await test_session.commit()

    @pytest.mark.asyncio
    async def test_user_notes_relationship(self, test_session):
        """Test user-notes relationship."""
        user = User(username="noteowner", password_hash="hash")
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # Create notes
        note1 = Note(title="Note 1", content="Content 1", owner_id=user.id)
        note2 = Note(title="Note 2", content="Content 2", owner_id=user.id)

        test_session.add_all([note1, note2])
        await test_session.commit()
        await test_session.refresh(user)

        # Check relationship
        assert len(user.notes) == 2
        assert note1 in user.notes
        assert note2 in user.notes

    @pytest.mark.asyncio
    async def test_user_cascade_delete_notes(self, test_session):
        """Test that deleting user cascades to notes."""
        user = User(username="tobedeleted", password_hash="hash")
        test_session.add(user)
        await test_session.commit()

        note = Note(title="To be deleted", content="Content", owner_id=user.id)
        test_session.add(note)
        await test_session.commit()

        user_id = user.id
        note_id = note.id

        # Delete user
        await test_session.delete(user)
        await test_session.commit()

        # Check that note is also deleted
        deleted_note = await test_session.get(Note, note_id)
        assert deleted_note is None

    @pytest.mark.asyncio
    async def test_user_shares_given_relationship(self, test_session):
        """Test shares_given relationship."""
        user1 = User(username="sharer", password_hash="hash")
        user2 = User(username="receiver", password_hash="hash")

        test_session.add_all([user1, user2])
        await test_session.commit()
        await test_session.refresh(user1)
        await test_session.refresh(user2)

        # Create note
        note = Note(title="Shared Note", content="Content", owner_id=user1.id)
        test_session.add(note)
        await test_session.commit()
        await test_session.refresh(note)

        # Create share
        share = Share(
            note_id=note.id,
            shared_by_user_id=user1.id,
            shared_with_user_id=user2.id,
            permission="read",
        )
        test_session.add(share)
        await test_session.commit()
        await test_session.refresh(user1)

        assert len(user1.shares_given) == 1
        assert share in user1.shares_given

    @pytest.mark.asyncio
    async def test_user_shares_received_relationship(self, test_session):
        """Test shares_received relationship."""
        user1 = User(username="sharer", password_hash="hash")
        user2 = User(username="receiver", password_hash="hash")

        test_session.add_all([user1, user2])
        await test_session.commit()
        await test_session.refresh(user1)
        await test_session.refresh(user2)

        # Create note
        note = Note(title="Shared Note", content="Content", owner_id=user1.id)
        test_session.add(note)
        await test_session.commit()
        await test_session.refresh(note)

        # Create share
        share = Share(
            note_id=note.id,
            shared_by_user_id=user1.id,
            shared_with_user_id=user2.id,
            permission="read",
        )
        test_session.add(share)
        await test_session.commit()
        await test_session.refresh(user2)

        assert len(user2.shares_received) == 1
        assert share in user2.shares_received

    @pytest.mark.asyncio
    async def test_user_refresh_tokens_relationship(self, test_session):
        """Test refresh_tokens relationship."""
        user = User(username="tokenuser", password_hash="hash")
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # Create refresh tokens
        token1 = RefreshToken(token="token1", user_id=user.id, expires_at=datetime.utcnow())
        token2 = RefreshToken(token="token2", user_id=user.id, expires_at=datetime.utcnow())

        test_session.add_all([token1, token2])
        await test_session.commit()
        await test_session.refresh(user)

        assert len(user.refresh_tokens) == 2
        assert token1 in user.refresh_tokens
        assert token2 in user.refresh_tokens

    @pytest.mark.asyncio
    async def test_user_field_constraints(self, test_session):
        """Test field constraints."""
        # Username too long (max 50)
        with pytest.raises(Exception):
            user = User(username="a" * 51, password_hash="hash")  # Too long
            test_session.add(user)
            await test_session.commit()

        await test_session.rollback()

        # Full name too long (max 100)
        with pytest.raises(Exception):
            user = User(username="validuser", password_hash="hash", full_name="a" * 101)  # Too long
            test_session.add(user)
            await test_session.commit()

    @pytest.mark.asyncio
    async def test_user_inactive(self, test_session):
        """Test inactive user."""
        user = User(username="inactiveuser", password_hash="hash", is_active=False)

        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        assert user.is_active is False

    @pytest.mark.asyncio
    async def test_user_unverified(self, test_session):
        """Test unverified user."""
        user = User(username="unverifieduser", password_hash="hash", is_verified=False)

        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        assert user.is_verified is False
