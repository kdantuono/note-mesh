"""
Unit tests for Tag model.
"""

import pytest
import uuid

from src.notemesh.core.models.user import User
from src.notemesh.core.models.note import Note
from src.notemesh.core.models.tag import Tag, NoteTag


class TestTagModel:
    """Test Tag model functionality."""
    
    @pytest.mark.asyncio
    async def test_create_tag(self, test_session):
        """Test creating a tag."""
        tag = Tag(
            name="python",
            description="Python programming language",
            color="#3776AB"
        )
        
        test_session.add(tag)
        await test_session.commit()
        await test_session.refresh(tag)
        
        assert tag.id is not None
        assert isinstance(tag.id, uuid.UUID)
        assert tag.name == "python"
        assert tag.description == "Python programming language"
        assert tag.color == "#3776AB"
        assert tag.usage_count == 0
        assert tag.created_by_user_id is None
    
    @pytest.mark.asyncio
    async def test_tag_defaults(self, test_session):
        """Test tag with default values."""
        tag = Tag(name="minimal")
        
        test_session.add(tag)
        await test_session.commit()
        await test_session.refresh(tag)
        
        assert tag.description is None
        assert tag.color is None
        assert tag.usage_count == 0
        assert tag.created_by_user_id is None
    
    @pytest.mark.asyncio
    async def test_tag_repr(self, test_session):
        """Test tag string representation."""
        tag = Tag(name="test-tag")
        
        test_session.add(tag)
        await test_session.commit()
        
        assert repr(tag) == "<Tag(name='test-tag')>"
    
    @pytest.mark.asyncio
    async def test_tag_unique_name(self, test_session):
        """Test that tag name must be unique."""
        tag1 = Tag(name="duplicate")
        tag2 = Tag(name="duplicate")
        
        test_session.add(tag1)
        await test_session.commit()
        
        test_session.add(tag2)
        
        # Should raise integrity error on duplicate name
        with pytest.raises(Exception):  # IntegrityError
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_tag_with_creator(self, test_session, test_user):
        """Test tag with creator user."""
        tag = Tag(
            name="user-tag",
            created_by_user_id=test_user.id
        )
        
        test_session.add(tag)
        await test_session.commit()
        await test_session.refresh(tag)
        
        assert tag.created_by_user_id == test_user.id
        assert tag.created_by_user == test_user
    
    @pytest.mark.asyncio
    async def test_tag_notes_relationship(self, test_session, test_user):
        """Test tag-notes many-to-many relationship."""
        tag = Tag(name="relationship-test")
        test_session.add(tag)
        
        note1 = Note(
            title="Note 1",
            content="Content 1",
            owner_id=test_user.id
        )
        note2 = Note(
            title="Note 2",
            content="Content 2",
            owner_id=test_user.id
        )
        
        test_session.add_all([note1, note2])
        await test_session.commit()
        
        # Add tag to notes
        tag.notes.append(note1)
        tag.notes.append(note2)
        await test_session.commit()
        await test_session.refresh(tag)
        
        assert len(tag.notes) == 2
        assert note1 in tag.notes
        assert note2 in tag.notes
    
    @pytest.mark.asyncio
    async def test_tag_usage_count(self, test_session):
        """Test tag usage count."""
        tag = Tag(name="usage-test", usage_count=5)
        
        test_session.add(tag)
        await test_session.commit()
        await test_session.refresh(tag)
        
        assert tag.usage_count == 5
        
        # Update usage count
        tag.usage_count = 10
        await test_session.commit()
        await test_session.refresh(tag)
        
        assert tag.usage_count == 10
    
    @pytest.mark.asyncio
    async def test_tag_color_validation(self, test_session):
        """Test tag color field."""
        # Valid hex color
        tag1 = Tag(name="red", color="#FF0000")
        test_session.add(tag1)
        await test_session.commit()
        
        assert tag1.color == "#FF0000"
        
        # Short hex color
        tag2 = Tag(name="blue", color="#00F")
        test_session.add(tag2)
        await test_session.commit()
        
        assert tag2.color == "#00F"
        
        # Invalid color (too long - max 7 chars)
        with pytest.raises(Exception):
            tag3 = Tag(name="invalid", color="#FF00FF00")  # 9 chars
            test_session.add(tag3)
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_tag_field_constraints(self, test_session):
        """Test field constraints."""
        # Name too long (max 50)
        with pytest.raises(Exception):
            tag = Tag(name="a" * 51)  # Too long
            test_session.add(tag)
            await test_session.commit()
        
        await test_session.rollback()
        
        # Description too long (max 200)
        with pytest.raises(Exception):
            tag = Tag(
                name="valid",
                description="a" * 201  # Too long
            )
            test_session.add(tag)
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_tag_cascade_behavior(self, test_session, test_user):
        """Test cascade behavior when tag is deleted."""
        tag = Tag(name="to-delete")
        note = Note(
            title="Tagged Note",
            content="Content",
            owner_id=test_user.id
        )
        
        test_session.add_all([tag, note])
        await test_session.commit()
        
        # Associate tag with note
        note.tags.append(tag)
        await test_session.commit()
        
        tag_id = tag.id
        note_id = note.id
        
        # Delete tag
        await test_session.delete(tag)
        await test_session.commit()
        
        # Note should still exist
        existing_note = await test_session.get(Note, note_id)
        assert existing_note is not None
        
        # But the tag association should be gone
        await test_session.refresh(existing_note)
        assert len(existing_note.tags) == 0
    
    @pytest.mark.asyncio
    async def test_note_tag_association(self, test_session, test_user):
        """Test NoteTag association table."""
        tag = Tag(name="association-test")
        note = Note(
            title="Note",
            content="Content",
            owner_id=test_user.id
        )
        
        test_session.add_all([tag, note])
        await test_session.commit()
        await test_session.refresh(tag)
        await test_session.refresh(note)
        
        # Create association
        note_tag = NoteTag(note_id=note.id, tag_id=tag.id)
        test_session.add(note_tag)
        await test_session.commit()
        
        # Check relationships through association
        await test_session.refresh(note)
        await test_session.refresh(tag)
        
        assert len(note.note_tags) == 1
        assert len(tag.note_tags) == 1
        assert note.note_tags[0].tag_id == tag.id
        assert tag.note_tags[0].note_id == note.id
    
    @pytest.mark.asyncio
    async def test_tag_without_creator_user_deleted(self, test_session):
        """Test tag behavior when creator user is deleted."""
        # Create user
        user = User(username="tagcreator", password_hash="hash")
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        # Create tag with creator
        tag = Tag(
            name="orphan-tag",
            created_by_user_id=user.id
        )
        test_session.add(tag)
        await test_session.commit()
        
        tag_id = tag.id
        
        # Delete user (should set created_by_user_id to NULL due to SET NULL)
        await test_session.delete(user)
        await test_session.commit()
        
        # Tag should still exist
        existing_tag = await test_session.get(Tag, tag_id)
        assert existing_tag is not None
        assert existing_tag.created_by_user_id is None