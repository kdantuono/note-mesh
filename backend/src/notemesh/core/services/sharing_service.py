"""Sharing service implementation."""

from typing import Dict, List
from uuid import UUID
from datetime import datetime, timezone

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
from ..schemas.notes import NoteListItem
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

            # Check if share already exists
            existing_share = await self.share_repo.get_existing_share(
                request.note_id, target_user.id
            )
            if existing_share:
                # Update existing share instead of creating duplicate
                share = await self.share_repo.update_share(
                    existing_share.id,
                    {
                        "permission": request.permission_level,
                        "share_message": request.message,
                        "status": "active",  # Reactivate if was revoked
                    },
                )
            else:
                # Create new share
                share_data = {
                    "note_id": request.note_id,
                    "shared_by_user_id": user_id,
                    "shared_with_user_id": target_user.id,
                    "permission": request.permission_level,
                    "share_message": request.message,
                    "expires_at": request.expires_at,
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
        try:
            access_info = await self.share_repo.check_note_access(note_id, user_id)
        except Exception:
            # If there's an error checking access, assume no access
            access_info = {"can_read": False}

        if not access_info["can_read"]:
            # Return 404 instead of 403 to prevent information leakage about note existence
            # This is consistent with NoteService.get_note() behavior
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
            )

        # Get the note
        note = await self.note_repo.get_by_id(note_id)
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        # Get the owner info
        owner = await self.user_repo.get_by_id(note.owner_id)

        # Build response, filling required fields with available info/defaults

        permission_level = "write" if access_info.get("can_write") else "read"

        return SharedNoteResponse(
            id=note.id,
            title=note.title,
            content=note.content,
            tags=[tag.name for tag in note.tags] if getattr(note, "tags", None) else [],
            hyperlinks=getattr(note, "hyperlinks", []) or [],
            owner_id=note.owner_id,
            owner_username=owner.username if owner else "Unknown",
            owner_display_name=(
                owner.full_name
                if owner and hasattr(owner, "full_name")
                else (owner.username if owner else "Unknown")
            ),
            shared_by_id=note.owner_id,  # Fallback to owner as sharer
            shared_by_username=owner.username if owner else "Unknown",
            permission_level=permission_level,
            shared_at=getattr(note, "created_at", datetime.now(timezone.utc)),
            expires_at=None,
            share_message=None,
            created_at=getattr(note, "created_at", datetime.now(timezone.utc)),
            updated_at=getattr(note, "updated_at", datetime.now(timezone.utc)),
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

        shared_with_user_id = getattr(share, "shared_with_user_id", None)
        if not shared_with_user_id and getattr(share, "shared_with_user", None):
            shared_with_user_id = getattr(share.shared_with_user, "id", None)

        # Create complete note data for dashboard display
        note_data = None
        if getattr(share, "note", None):
            note = share.note
            # Only create NoteListItem if note has required fields (id, title, owner_id)
            if hasattr(note, 'id') and hasattr(note, 'title') and hasattr(note, 'owner_id'):
                # Get owner info for note
                owner_username = None
                owner_display_name = None
                if hasattr(note, 'owner') and note.owner:
                    owner_username = note.owner.username
                    owner_display_name = getattr(note.owner, 'full_name', None)
                elif hasattr(share, 'shared_by_user') and share.shared_by_user:
                    # Fallback to sharer info if note.owner not available
                    owner_username = share.shared_by_user.username
                    owner_display_name = getattr(share.shared_by_user, 'full_name', None)

                note_data = NoteListItem(
                    id=note.id,
                    title=note.title,
                    content_preview=getattr(note, 'content', '')[:200] + ("..." if len(getattr(note, 'content', '')) > 200 else ""),
                    tags=[tag.name if hasattr(tag, 'name') else str(tag) for tag in getattr(note, 'tags', [])],
                    owner_id=note.owner_id,
                    owner_username=owner_username,
                    owner_display_name=owner_display_name,
                    is_shared=True,
                    is_owned=False,  # This is a shared note from recipient perspective
                    can_edit=getattr(share, "permission", "read") == "write",
                    created_at=getattr(note, 'created_at', datetime.now(timezone.utc)),
                    updated_at=getattr(note, 'updated_at', datetime.now(timezone.utc))
                )

        return ShareResponse(
            id=share.id,
            note_id=share.note_id,
            note_title=share.note.title if getattr(share, "note", None) else "Unknown",
            shared_with_user_id=shared_with_user_id,
            shared_with_username=(
                share.shared_with_user.username
                if getattr(share, "shared_with_user", None)
                else "Unknown"
            ),
            shared_with_display_name=(
                share.shared_with_user.full_name
                if getattr(share, "shared_with_user", None)
                and hasattr(share.shared_with_user, "full_name")
                else "Unknown"
            ),
            permission_level=getattr(share, "permission", "read"),
            message=getattr(share, "share_message", None),
            note=note_data,  # Include complete note data
            shared_at=getattr(share, "created_at", datetime.now(timezone.utc)),
            expires_at=getattr(share, "expires_at", None),
            last_accessed=getattr(share, "last_accessed", None),
            is_active=getattr(share, "is_active", True),
            access_count=getattr(share, "access_count", 0),
        )

    # Additional methods for test compatibility
    async def create_share(self, user_id: UUID, request: ShareRequest) -> ShareResponse:
        """Alias for share_note - creates single share."""
        results = await self.share_note(user_id, request)
        return results[0] if results else None

    async def delete_share(self, user_id: UUID, share_id: UUID) -> bool:
        """Alias for revoke_share."""
        return await self.revoke_share(user_id, share_id)

    async def get_shares_given(self, user_id: UUID, request: ShareListRequest) -> ShareListResponse:
        """Get shares given by user."""
        request.type = "given"
        return await self.list_shares(user_id, request)

    async def get_shares_received(self, user_id: UUID, request: ShareListRequest) -> ShareListResponse:
        """Get shares received by user."""
        request.type = "received"
        return await self.list_shares(user_id, request)

    async def get_note_shares(self, user_id: UUID, note_id: UUID) -> List[ShareResponse]:
        """Get all shares for a specific note (only if user owns the note)."""
        # Verify note exists and user owns it
        note = await self.note_repo.get_by_id_and_user(note_id, user_id)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Note not found or not owned by user"
            )

        shares = await self.share_repo.get_note_shares(note_id)
        return [self._share_to_response(share) for share in shares]
