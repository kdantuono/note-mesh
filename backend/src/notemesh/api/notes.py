"""Notes API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db_session
from ..core.services import NoteService
from ..core.schemas.notes import (
    NoteCreate, NoteUpdate, NoteResponse, NoteListResponse
)
from ..middleware.auth import get_current_user_id

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("/", response_model=NoteResponse, status_code=201)
async def create_note(
    request: NoteCreate,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Create a new note."""
    note_service = NoteService(session)
    return await note_service.create_note(current_user_id, request)


@router.get("/", response_model=NoteListResponse)
async def list_notes(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    tags: Optional[List[str]] = Query(None),
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """List user notes with optional tag filtering."""
    note_service = NoteService(session)
    return await note_service.list_user_notes(
        user_id=current_user_id,
        page=page,
        per_page=per_page,
        tag_filter=tags
    )


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get a specific note."""
    note_service = NoteService(session)
    return await note_service.get_note(note_id, current_user_id)


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: UUID,
    request: NoteUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Update a note."""
    note_service = NoteService(session)
    return await note_service.update_note(note_id, current_user_id, request)


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Delete a note."""
    note_service = NoteService(session)
    await note_service.delete_note(note_id, current_user_id)


@router.get("/tags/", response_model=List[str])
async def get_available_tags(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Get all available tags for the user."""
    note_service = NoteService(session)
    return await note_service.get_available_tags(current_user_id)


@router.post("/validate-links", response_model=dict)
async def validate_hyperlinks(
    links: List[str],
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """Validate a list of hyperlinks."""
    note_service = NoteService(session)
    return await note_service.validate_hyperlinks(links)