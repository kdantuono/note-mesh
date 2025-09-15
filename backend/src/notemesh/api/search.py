"""Search API endpoints."""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.schemas.notes import NoteSearchRequest, NoteSearchResponse
from ..core.services import SearchService
from ..database import get_db_session
from ..middleware.auth import get_current_user_id

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/notes", response_model=NoteSearchResponse)
async def search_notes(
    q: str = Query(..., description="Search query"),
    tags: List[str] = Query(None, description="Tag filters"),
    page: int = Query(1, ge=1),
    per_page: int = Query(9, ge=1, le=100),
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Search notes by content and tags."""
    search_service = SearchService(session)
    request = NoteSearchRequest(query=q, tags=tags, page=page, per_page=per_page)
    return await search_service.search_notes(current_user_id, request)


@router.get("/tags/suggest", response_model=List[str])
async def suggest_tags(
    q: str = Query(..., description="Tag query"),
    limit: int = Query(10, ge=1, le=50),
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Get tag suggestions based on query."""
    search_service = SearchService(session)
    return await search_service.suggest_tags(current_user_id, q, limit)


@router.get("/stats", response_model=Dict[str, Any])
async def get_search_stats(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Get search statistics for current user."""
    search_service = SearchService(session)
    return await search_service.get_search_stats(current_user_id)
