"""Note repository for database operations."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.note import Note
from ..models.tag import Tag


class NoteRepository:
    """Repository for note database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_note(self, note_data: dict) -> Note:
        """Create new note."""
        note = Note(**note_data)
        self.session.add(note)
        await self.session.commit()
        await self.session.refresh(note)
        return note

    async def get_by_id(self, note_id: UUID) -> Optional[Note]:
        """Get note by ID with tags."""
        stmt = select(Note).options(selectinload(Note.tags)).where(Note.id == note_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_and_user(self, note_id: UUID, user_id: UUID) -> Optional[Note]:
        """Get note by ID if owned by user."""
        stmt = (
            select(Note)
            .options(selectinload(Note.tags))
            .where(and_(Note.id == note_id, Note.owner_id == user_id))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_note(self, note_id: UUID, user_id: UUID, update_data: dict) -> Optional[Note]:
        """Update note if owned by user."""
        note = await self.get_by_id_and_user(note_id, user_id)
        if not note:
            return None

        for key, value in update_data.items():
            if key != "tags":  # Handle tags separately
                setattr(note, key, value)

        await self.session.commit()
        await self.session.refresh(note, ["tags"])
        return note

    async def delete_note(self, note_id: UUID, user_id: UUID) -> bool:
        """Delete note if owned by user."""
        note = await self.get_by_id_and_user(note_id, user_id)
        if not note:
            return False

        await self.session.delete(note)
        await self.session.commit()
        return True

    async def list_user_notes(
        self,
        user_id: UUID,
        page: int = 1,
        per_page: int = 20,
        tag_filter: Optional[List[str]] = None,
    ) -> tuple[List[Note], int]:
        """List user notes with pagination and optional tag filter."""
        offset = (page - 1) * per_page

        stmt = select(Note).options(selectinload(Note.tags)).where(Note.owner_id == user_id)

        if tag_filter:
            # Join with tags and filter
            stmt = stmt.join(Note.tags).where(Tag.name.in_(tag_filter))

        # Get total count
        count_stmt = select(func.count(Note.id.distinct())).where(Note.owner_id == user_id)
        if tag_filter:
            count_stmt = count_stmt.join(Note.tags).where(Tag.name.in_(tag_filter))

        total_result = await self.session.execute(count_stmt)
        total_count = total_result.scalar()

        # Get paginated results
        stmt = stmt.order_by(desc(Note.updated_at)).offset(offset).limit(per_page).distinct()
        result = await self.session.execute(stmt)
        notes = result.scalars().all()

        return list(notes), total_count

    async def get_user_tags(self, user_id: UUID) -> List[str]:
        """Get all unique tags for user's notes."""
        stmt = (
            select(Tag.name.distinct())
            .join(Note.tags)
            .where(Note.owner_id == user_id)
            .order_by(Tag.name)
        )
        result = await self.session.execute(stmt)
        return [tag for tag in result.scalars()]

    async def search_notes(
        self, user_id: UUID, query: str, tag_filter: Optional[List[str]] = None
    ) -> List[Note]:
        """Search notes by content or title."""
        stmt = select(Note).options(selectinload(Note.tags)).where(Note.owner_id == user_id)

        # Full-text search on title and content
        search_condition = or_(Note.title.ilike(f"%{query}%"), Note.content.ilike(f"%{query}%"))
        stmt = stmt.where(search_condition)

        # Add tag filter
        if tag_filter:
            stmt = stmt.join(Note.tags).where(Tag.name.in_(tag_filter))

        stmt = stmt.order_by(desc(Note.updated_at)).distinct()
        result = await self.session.execute(stmt)
        return list(result.scalars())
