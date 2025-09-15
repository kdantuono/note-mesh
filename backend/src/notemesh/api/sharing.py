"""Sharing API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.schemas.sharing import (
    SharedNoteResponse,
    ShareListRequest,
    ShareListResponse,
    ShareRequest,
    ShareResponse,
    ShareStatsResponse,
)
from ..core.services import SharingService
from ..database import get_db_session
from ..middleware.auth import get_current_user_id

router = APIRouter(prefix="/sharing", tags=["sharing"])


@router.post("/", response_model=List[ShareResponse], status_code=201)
async def share_note(
    request: ShareRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Share a note with other users."""
    sharing_service = SharingService(session)
    return await sharing_service.share_note(current_user_id, request)


@router.delete("/{share_id}", status_code=204)
async def revoke_share(
    share_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Revoke a note share."""
    sharing_service = SharingService(session)
    await sharing_service.revoke_share(current_user_id, share_id)


@router.get("/notes/{note_id}", response_model=SharedNoteResponse)
async def get_shared_note(
    note_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Get a shared note (for recipients)."""
    sharing_service = SharingService(session)
    return await sharing_service.get_shared_note(note_id, current_user_id)


@router.get("/", response_model=ShareListResponse)
async def list_shares(
    type: str = Query("given", pattern="^(given|received)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(9, ge=1, le=100),
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """List shares (given or received)."""
    sharing_service = SharingService(session)
    request = ShareListRequest(type=type, page=page, per_page=per_page)
    return await sharing_service.list_shares(current_user_id, request)


@router.get("/stats", response_model=ShareStatsResponse)
async def get_share_stats(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Get sharing statistics."""
    sharing_service = SharingService(session)
    return await sharing_service.get_share_stats(current_user_id)


@router.get("/notes/{note_id}/access")
async def check_note_access(
    note_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Check access permissions for a note."""
    sharing_service = SharingService(session)
    return await sharing_service.check_note_access(note_id, current_user_id)
