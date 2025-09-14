"""Share repository for database operations."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.note import Note
from ..models.share import Share


class ShareRepository:
    """Repository for share database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_share(self, share_data: dict) -> Share:
        """Create new share."""
        share = Share(**share_data)
        self.session.add(share)
        await self.session.commit()
        await self.session.refresh(share, ["note", "shared_by_user", "shared_with_user"])
        return share

    async def get_by_id(self, share_id: UUID) -> Optional[Share]:
        """Get share by ID."""
        stmt = (
            select(Share)
            .options(
                selectinload(Share.note),
                selectinload(Share.shared_by_user),
                selectinload(Share.shared_with_user),
            )
            .where(Share.id == share_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_share(self, share_id: UUID, user_id: UUID) -> Optional[Share]:
        """Get share if user is owner."""
        stmt = (
            select(Share)
            .options(
                selectinload(Share.note),
                selectinload(Share.shared_by_user),
                selectinload(Share.shared_with_user),
            )
            .where(and_(Share.id == share_id, Share.shared_by_user_id == user_id))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_share(self, share_id: UUID, user_id: UUID) -> bool:
        """Delete share if owned by user."""
        share = await self.get_user_share(share_id, user_id)
        if not share:
            return False

        await self.session.delete(share)
        await self.session.commit()
        return True

    async def list_shares_given(
        self, user_id: UUID, page: int = 1, per_page: int = 20
    ) -> tuple[List[Share], int]:
        """List shares created by user."""
        offset = (page - 1) * per_page

        # Count query
        count_stmt = select(func.count(Share.id)).where(Share.shared_by_user_id == user_id)
        total_result = await self.session.execute(count_stmt)
        total_count = total_result.scalar()

        # Data query
        stmt = (
            select(Share)
            .options(selectinload(Share.note), selectinload(Share.shared_with_user))
            .where(Share.shared_by_user_id == user_id)
            .order_by(desc(Share.created_at))
            .offset(offset)
            .limit(per_page)
        )

        result = await self.session.execute(stmt)
        shares = list(result.scalars())

        return shares, total_count

    async def list_shares_received(
        self, user_id: UUID, page: int = 1, per_page: int = 20
    ) -> tuple[List[Share], int]:
        """List shares received by user."""
        offset = (page - 1) * per_page

        # Count query
        count_stmt = select(func.count(Share.id)).where(Share.shared_with_user_id == user_id)
        total_result = await self.session.execute(count_stmt)
        total_count = total_result.scalar()

        # Data query
        stmt = (
            select(Share)
            .options(selectinload(Share.note), selectinload(Share.shared_by_user))
            .where(Share.shared_with_user_id == user_id)
            .order_by(desc(Share.created_at))
            .offset(offset)
            .limit(per_page)
        )

        result = await self.session.execute(stmt)
        shares = list(result.scalars())

        return shares, total_count

    async def check_note_access(self, note_id: UUID, user_id: UUID) -> dict:
        """Check user's access permissions to a note."""
        # Check if user owns the note
        note_stmt = select(Note).where(and_(Note.id == note_id, Note.owner_id == user_id))
        note_result = await self.session.execute(note_stmt)
        is_owner = note_result.scalar_one_or_none() is not None

        # Check if note is shared with user
        share_stmt = select(Share).where(
            and_(Share.note_id == note_id, Share.shared_with_user_id == user_id)
        )
        share_result = await self.session.execute(share_stmt)
        shared_note = share_result.scalar_one_or_none()

        return {
            "can_read": is_owner or shared_note is not None,
            "can_write": is_owner or (shared_note and shared_note.permission == "write"),
            "can_share": is_owner,
            "is_owner": is_owner,
        }

    async def get_share_stats(self, user_id: UUID) -> dict:
        """Get sharing statistics for user."""
        # Count shares given
        given_stmt = select(func.count(Share.id)).where(Share.shared_by_user_id == user_id)
        given_result = await self.session.execute(given_stmt)
        shares_given = given_result.scalar()

        # Count shares received
        received_stmt = select(func.count(Share.id)).where(Share.shared_with_user_id == user_id)
        received_result = await self.session.execute(received_stmt)
        shares_received = received_result.scalar()

        # Count unique notes shared
        unique_notes_stmt = select(func.count(Share.note_id.distinct())).where(
            Share.shared_by_user_id == user_id
        )
        unique_notes_result = await self.session.execute(unique_notes_stmt)
        unique_notes_shared = unique_notes_result.scalar()

        return {
            "shares_given": shares_given,
            "shares_received": shares_received,
            "unique_notes_shared": unique_notes_shared,
        }

    async def get_existing_share(self, note_id: UUID, shared_with_user_id: UUID) -> Optional[Share]:
        """Get existing share for note and user."""
        stmt = (
            select(Share)
            .options(
                selectinload(Share.note),
                selectinload(Share.shared_by_user),
                selectinload(Share.shared_with_user),
            )
            .where(
                and_(
                    Share.note_id == note_id,
                    Share.shared_with_user_id == shared_with_user_id
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_share(self, share_id: UUID, update_data: dict) -> Share:
        """Update existing share."""
        share = await self.get_by_id(share_id)
        if not share:
            raise ValueError(f"Share {share_id} not found")

        for key, value in update_data.items():
            setattr(share, key, value)

        await self.session.commit()
        await self.session.refresh(share, ["note", "shared_by_user", "shared_with_user"])
        return share
