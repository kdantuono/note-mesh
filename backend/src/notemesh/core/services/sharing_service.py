"""Sharing service implementation."""

from typing import Dict, List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.note_repository import NoteRepository
from ..repositories.share_repository import ShareRepository
from ..repositories.user_repository import UserRepository
from ..schemas.sharing import (
    SharedNoteResponse,
    ShareListRequest,
    ShareListResponse,
    ShareRequest,
    ShareResponse,
    ShareStatsResponse,
)
from .interfaces import ISharingService


class SharingService(ISharingService):
    """Sharing service implementation."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.share_repo = ShareRepository(session)
        self.user_repo = UserRepository(session)
        self.note_repo = NoteRepository(session)

    async def share_note(self, user_id: UUID, request: ShareRequest) -> List[ShareResponse]:
        """Share note with other users."""
        # Verify note exists and user owns it
        note = await self.note_repo.get_by_id_and_user(request.note_id, user_id)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Note not found or not owned by user"
            )

        # Verify all target users exist
        share_responses = []
        for username in request.shared_with_usernames:
            target_user = await self.user_repo.get_by_username(username)
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{username}' not found"
                )

            if target_user.id == user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot share note with yourself",
                )

            # Create share
            share_data = {
                "note_id": request.note_id,
                "shared_by_user_id": user_id,
                "shared_with_user_id": target_user.id,
                "permission_level": request.permission_level,
                "message": request.message,
            }

            share = await self.share_repo.create_share(share_data)
            share_responses.append(self._share_to_response(share))

        return share_responses

    async def revoke_share(self, user_id: UUID, share_id: UUID) -> bool:
        """Revoke note share."""
        return await self.share_repo.delete_share(share_id, user_id)

    async def get_shared_note(self, note_id: UUID, user_id: UUID) -> SharedNoteResponse:
        """Get shared note for recipient."""
        # Check if user has access to this note
        access_info = await self.share_repo.check_note_access(note_id, user_id)
        if not access_info["can_read"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="No permission to access this note"
            )

        # Get the note
        note = await self.note_repo.get_by_id(note_id)
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        # Get the owner info
        owner = await self.user_repo.get_by_id(note.owner_id)

        # Build response, filling required fields with available info/defaults
        from datetime import datetime

        permission_level = "write" if access_info.get("can_write") else "read"

        return SharedNoteResponse(
            id=note.id,
            title=note.title,
            content=note.content,
            tags=[tag.name for tag in note.tags] if getattr(note, "tags", None) else [],
            hyperlinks=getattr(note, "hyperlinks", []) or [],
            owner_id=note.owner_id,
            owner_username=owner.username if owner else "Unknown",
            owner_display_name=owner.full_name
            if owner and hasattr(owner, "full_name")
            else (owner.username if owner else "Unknown"),
            shared_by_id=note.owner_id,  # Fallback to owner as sharer
            shared_by_username=owner.username if owner else "Unknown",
            permission_level=permission_level,
            shared_at=getattr(note, "created_at", datetime.utcnow()),
            expires_at=None,
            share_message=None,
            created_at=getattr(note, "created_at", datetime.utcnow()),
            updated_at=getattr(note, "updated_at", datetime.utcnow()),
            last_accessed=None,
            can_write=access_info.get("can_write", False),
            can_share=access_info.get("can_share", False),
        )

    async def list_shares(self, user_id: UUID, request: ShareListRequest) -> ShareListResponse:
        """List user shares."""
        page = request.page or 1
        per_page = request.per_page or 20

        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20

        if request.type == "given":
            shares, total_count = await self.share_repo.list_shares_given(user_id, page, per_page)
        elif request.type == "received":
            shares, total_count = await self.share_repo.list_shares_received(
                user_id, page, per_page
            )
        else:
            # Default to given shares
            shares, total_count = await self.share_repo.list_shares_given(user_id, page, per_page)

        share_responses = [self._share_to_response(share) for share in shares]

        return ShareListResponse(
            shares=share_responses,
            total_count=total_count,
            page=page,
            per_page=per_page,
            total_pages=(total_count + per_page - 1) // per_page,
            type=request.type or "given",
        )

    async def get_share_stats(self, user_id: UUID) -> ShareStatsResponse:
        """Get sharing statistics."""
        stats = await self.share_repo.get_share_stats(user_id)

        return ShareStatsResponse(
            shares_given=stats["shares_given"],
            shares_received=stats["shares_received"],
            unique_notes_shared=stats["unique_notes_shared"],
        )

    async def check_note_access(self, note_id: UUID, user_id: UUID) -> Dict[str, bool]:
        """Check user note permissions."""
        return await self.share_repo.check_note_access(note_id, user_id)

    def _share_to_response(self, share) -> ShareResponse:
        """Convert share model to response."""
        from datetime import datetime

        shared_with_user_id = getattr(share, "shared_with_user_id", None)
        if not shared_with_user_id and getattr(share, "shared_with_user", None):
            shared_with_user_id = getattr(share.shared_with_user, "id", None)

        return ShareResponse(
            id=share.id,
            note_id=share.note_id,
            note_title=share.note.title if getattr(share, "note", None) else "Unknown",
            shared_with_user_id=shared_with_user_id,
            shared_with_username=share.shared_with_user.username
            if getattr(share, "shared_with_user", None)
            else "Unknown",
            shared_with_display_name=share.shared_with_user.full_name
            if getattr(share, "shared_with_user", None)
            and hasattr(share.shared_with_user, "full_name")
            else "Unknown",
            permission_level=getattr(share, "permission_level", "read"),
            message=getattr(share, "message", None),
            shared_at=getattr(share, "created_at", datetime.utcnow()),
            expires_at=getattr(share, "expires_at", None),
            last_accessed=getattr(share, "last_accessed", None),
            is_active=getattr(share, "is_active", True),
            access_count=getattr(share, "access_count", 0),
        )
