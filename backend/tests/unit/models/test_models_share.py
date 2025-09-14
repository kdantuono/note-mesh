"""
Unit tests for Share model.
"""

import pytest
import uuid
from datetime import datetime, timedelta

from src.notemesh.core.models.user import User
from src.notemesh.core.models.note import Note
from src.notemesh.core.models.share import Share, ShareStatus


class TestShareModel:
    """Test Share model functionality."""
    
    @pytest.mark.asyncio
    async def test_create_share(self, test_session):
        """Test creating a share."""
        # Create users
        owner = User(username="owner", password_hash="hash")
        recipient = User(username="recipient", password_hash="hash")
        test_session.add_all([owner, recipient])
        await test_session.commit()
        await test_session.refresh(owner)
        await test_session.refresh(recipient)
        
        # Create note
        note = Note(
            title="Shared Note",
            content="Content to share",
            owner_id=owner.id
        )
        test_session.add(note)
        await test_session.commit()
        await test_session.refresh(note)
        
        # Create share
        share = Share(
            note_id=note.id,
            shared_by_user_id=owner.id,
            shared_with_user_id=recipient.id,
            share_message="Check this out!"
        )
        
        test_session.add(share)
        await test_session.commit()
        await test_session.refresh(share)
        
        assert share.id is not None
        assert share.note_id == note.id
        assert share.shared_by_user_id == owner.id
        assert share.shared_with_user_id == recipient.id
        assert share.status == ShareStatus.ACTIVE
        assert share.share_message == "Check this out!"
        assert share.access_count == 0
        assert share.last_accessed_at is None
        assert share.expires_at is None
    
    @pytest.mark.asyncio
    async def test_share_repr(self, test_session):
        """Test share string representation."""
        owner = User(username="owner2", password_hash="hash")
        recipient = User(username="recipient2", password_hash="hash")
        test_session.add_all([owner, recipient])
        await test_session.commit()
        
        note = Note(title="Note", content="Content", owner_id=owner.id)
        test_session.add(note)
        await test_session.commit()
        
        share = Share(
            note_id=note.id,
            shared_by_user_id=owner.id,
            shared_with_user_id=recipient.id
        )
        test_session.add(share)
        await test_session.commit()
        
        expected = f"<Share(note_id={note.id}, shared_with={recipient.id}, status={ShareStatus.ACTIVE})>"
        assert repr(share) == expected
    
    @pytest.mark.asyncio
    async def test_share_with_expiry(self, test_session, test_user):
        """Test share with expiration date."""
        recipient = User(username="recipient3", password_hash="hash")
        test_session.add(recipient)
        
        note = Note(title="Expiring", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        
        expires = datetime.utcnow() + timedelta(days=7)
        
        share = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=recipient.id,
            expires_at=expires
        )
        
        test_session.add(share)
        await test_session.commit()
        await test_session.refresh(share)
        
        assert share.expires_at == expires
        assert share.is_active is True
        assert share.is_expired is False
    
    @pytest.mark.asyncio
    async def test_share_expired(self, test_session, test_user):
        """Test expired share."""
        recipient = User(username="recipient4", password_hash="hash")
        test_session.add(recipient)
        
        note = Note(title="Expired", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        
        # Set expiry in the past
        expires = datetime.utcnow() - timedelta(hours=1)
        
        share = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=recipient.id,
            expires_at=expires
        )
        
        test_session.add(share)
        await test_session.commit()
        
        assert share.is_expired is True
        assert share.is_active is False  # Not active if expired
    
    @pytest.mark.asyncio
    async def test_share_revoke(self, test_session, test_user):
        """Test revoking a share."""
        recipient = User(username="recipient5", password_hash="hash")
        test_session.add(recipient)
        
        note = Note(title="To Revoke", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        
        share = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=recipient.id
        )
        
        test_session.add(share)
        await test_session.commit()
        
        # Revoke the share
        share.revoke()
        await test_session.commit()
        await test_session.refresh(share)
        
        assert share.status == ShareStatus.REVOKED
        assert share.is_active is False
    
    @pytest.mark.asyncio
    async def test_share_record_access(self, test_session, test_user):
        """Test recording access to a share."""
        recipient = User(username="recipient6", password_hash="hash")
        test_session.add(recipient)
        
        note = Note(title="Accessed", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        
        share = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=recipient.id
        )
        
        test_session.add(share)
        await test_session.commit()
        
        # Record access
        share.record_access()
        await test_session.commit()
        await test_session.refresh(share)
        
        assert share.access_count == 1
        assert share.last_accessed_at is not None
        
        # Record another access
        share.record_access()
        await test_session.commit()
        await test_session.refresh(share)
        
        assert share.access_count == 2
    
    @pytest.mark.asyncio
    async def test_share_check_permission_recipient(self, test_session, test_user):
        """Test permission checking for share recipient."""
        recipient = User(username="recipient7", password_hash="hash")
        test_session.add(recipient)
        await test_session.commit()
        await test_session.refresh(recipient)
        
        note = Note(title="Permissions", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        
        share = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=recipient.id
        )
        
        test_session.add(share)
        await test_session.commit()
        
        # Check permissions for recipient
        perms = share.check_permission(recipient.id)
        
        assert perms["can_read"] is True
        assert perms["can_edit"] is False
        assert perms["is_owner"] is False
        assert perms["is_recipient"] is True
    
    @pytest.mark.asyncio
    async def test_share_check_permission_owner(self, test_session, test_user):
        """Test permission checking for share owner."""
        recipient = User(username="recipient8", password_hash="hash")
        test_session.add(recipient)
        await test_session.commit()
        
        note = Note(title="Owner Perms", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        
        share = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=recipient.id
        )
        
        test_session.add(share)
        await test_session.commit()
        
        # Check permissions for owner
        perms = share.check_permission(test_user.id)
        
        assert perms["can_read"] is True
        assert perms["can_edit"] is True
        assert perms["is_owner"] is True
        assert perms["is_recipient"] is False
    
    @pytest.mark.asyncio
    async def test_share_check_permission_revoked(self, test_session, test_user):
        """Test permission checking for revoked share."""
        recipient = User(username="recipient9", password_hash="hash")
        test_session.add(recipient)
        await test_session.commit()
        await test_session.refresh(recipient)
        
        note = Note(title="Revoked Perms", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        
        share = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=recipient.id,
            status=ShareStatus.REVOKED
        )
        
        test_session.add(share)
        await test_session.commit()
        
        # Check permissions for revoked share
        perms = share.check_permission(recipient.id)
        
        assert perms["can_read"] is False  # Can't read revoked share
        assert perms["can_edit"] is False
        assert perms["is_recipient"] is True
    
    @pytest.mark.asyncio
    async def test_share_unique_constraint(self, test_session, test_user):
        """Test unique constraint on note_id and shared_with_user_id."""
        recipient = User(username="recipient10", password_hash="hash")
        test_session.add(recipient)
        
        note = Note(title="Unique Test", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        await test_session.refresh(recipient)
        
        # First share
        share1 = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=recipient.id
        )
        test_session.add(share1)
        await test_session.commit()
        
        # Try to create duplicate share
        share2 = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=recipient.id
        )
        test_session.add(share2)
        
        # Should raise integrity error
        with pytest.raises(Exception):
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_share_relationships(self, test_session, test_user):
        """Test share relationships."""
        recipient = User(username="recipient11", password_hash="hash")
        test_session.add(recipient)
        
        note = Note(title="Related", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        await test_session.refresh(recipient)
        
        share = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=recipient.id
        )
        
        test_session.add(share)
        await test_session.commit()
        await test_session.refresh(share)
        
        # Check relationships
        assert share.note == note
        assert share.shared_by_user == test_user
        assert share.shared_with_user == recipient
    
    @pytest.mark.asyncio
    async def test_share_cascade_delete(self, test_session, test_user):
        """Test cascade delete behavior."""
        recipient = User(username="recipient12", password_hash="hash")
        test_session.add(recipient)
        
        note = Note(title="Cascade Test", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        
        share = Share(
            note_id=note.id,
            shared_by_user_id=test_user.id,
            shared_with_user_id=recipient.id
        )
        test_session.add(share)
        await test_session.commit()
        
        share_id = share.id
        
        # Delete note - share should be deleted
        await test_session.delete(note)
        await test_session.commit()
        
        deleted_share = await test_session.get(Share, share_id)
        assert deleted_share is None
    
    @pytest.mark.asyncio
    async def test_share_field_constraints(self, test_session, test_user):
        """Test field constraints."""
        recipient = User(username="recipient13", password_hash="hash")
        test_session.add(recipient)
        
        note = Note(title="Constraints", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        
        # Share message too long (max 500)
        with pytest.raises(Exception):
            share = Share(
                note_id=note.id,
                shared_by_user_id=test_user.id,
                shared_with_user_id=recipient.id,
                share_message="a" * 501  # Too long
            )
            test_session.add(share)
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_share_status_enum(self, test_session, test_user):
        """Test ShareStatus enum values."""
        recipient = User(username="recipient14", password_hash="hash")
        test_session.add(recipient)
        
        note = Note(title="Status Test", content="Content", owner_id=test_user.id)
        test_session.add(note)
        await test_session.commit()
        
        # Test different status values
        for status in [ShareStatus.ACTIVE, ShareStatus.EXPIRED, ShareStatus.REVOKED, ShareStatus.PENDING]:
            share = Share(
                note_id=note.id,
                shared_by_user_id=test_user.id,
                shared_with_user_id=recipient.id,
                status=status
            )
            test_session.add(share)
            await test_session.commit()
            
            assert share.status == status
            
            # Clean up for next iteration
            await test_session.delete(share)
            await test_session.commit()