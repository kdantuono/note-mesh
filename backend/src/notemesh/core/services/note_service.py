"""Note service implementation."""

import re
from typing import Dict, Iterable, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..models.note import Note
from ..models.tag import NoteTag, Tag
from ..models.user import User
from ..repositories.note_repository import NoteRepository
from ..repositories.share_repository import ShareRepository
from ..repositories.user_repository import UserRepository
from ..schemas.notes import NoteCreate, NoteListItem, NoteListResponse, NoteResponse, NoteUpdate
from .interfaces import INoteService


class NoteService(INoteService):
    """Note service implementation."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.note_repo = NoteRepository(session)
        # Used to check access when the note is shared with the user
        self.share_repo = ShareRepository(session)
        # Used to fetch user information for owner details
        self.user_repo = UserRepository(session)

    async def create_note(self, user_id: UUID, request: NoteCreate) -> NoteResponse:
        """Create new note."""
        # Extract tags from content and add explicit tags
        content_tags = self._extract_tags_from_content(request.content)
        all_tags = set(content_tags + (request.tags or []))

        # Extract hyperlinks from content automatically
        content_links = self._extract_hyperlinks_from_text(request.content)

        # Merge explicit hyperlinks with extracted ones
        all_hyperlinks = list(set([str(link) for link in request.hyperlinks] + content_links))

        # Create note
        note_data = {
            "title": request.title,
            "content": request.content,
            "is_public": request.is_public,
            "hyperlinks": all_hyperlinks,
            "owner_id": user_id,
        }

        note = await self.note_repo.create_note(note_data)

        # Add tags
        if all_tags:
            await self._add_tags_to_note(note.id, list(all_tags))

        return await self._note_to_response(
            note, user_id, override_tags=list(all_tags) if all_tags else []
        )

    async def get_note(self, note_id: UUID, user_id: UUID) -> NoteResponse:
        """Get note by ID.

        Behavior:
        - If the current user owns the note, return it.
        - Otherwise, if the note is shared with the current user (read or write), allow access.
        - If neither, return 404 (to avoid information leakage about existence).
        """
        # First, try owned note fast-path
        note = await self.note_repo.get_by_id_and_user(note_id, user_id)
        if note:
            return await self._note_to_response(note, user_id)

        # If not owned, check if the note is shared with the user
        try:
            access = await self.share_repo.check_note_access(note_id, user_id)
        except Exception:
            access = {"can_read": False}

        if access.get("can_read"):
            note = await self.note_repo.get_by_id(note_id)
            if not note:
                # Shared link exists but note was deleted
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
            # Build response with correct can_edit based on share permission
            return await self._note_to_response(note, user_id, can_edit_override=bool(access.get("can_write", False)))

        # Not owned and not shared
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    async def update_note(self, note_id: UUID, user_id: UUID, request: NoteUpdate) -> NoteResponse:
        """Update existing note."""
        note = await self.note_repo.get_by_id_and_user(note_id, user_id)
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

        # Prepare update data
        update_data = {}
        if request.title is not None:
            update_data["title"] = request.title
        if request.content is not None:
            update_data["content"] = request.content
        if request.is_public is not None:
            update_data["is_public"] = request.is_public

        # Handle hyperlinks: extract from content and merge with explicit ones
        if request.content is not None or request.hyperlinks is not None:
            # Extract hyperlinks from content if content was updated
            content_links = []
            if request.content is not None:
                content_links = self._extract_hyperlinks_from_text(request.content)

            # Get explicit hyperlinks or keep existing ones
            explicit_links = []
            if request.hyperlinks is not None:
                explicit_links = [str(link) for link in request.hyperlinks]
            else:
                # Keep existing hyperlinks if none provided
                explicit_links = [str(link) for link in (note.hyperlinks or [])]

            # Merge and deduplicate
            all_hyperlinks = list(set(content_links + explicit_links))
            update_data["hyperlinks"] = all_hyperlinks

        # Update note
        updated_note = await self.note_repo.update_note(note_id, user_id, update_data)

        # Update tags if content changed
        if request.content is not None:
            content_tags = self._extract_tags_from_content(request.content)
            all_tags = set(content_tags + (request.tags or []))

            # Remove all existing tags and add new ones
            await self._clear_note_tags(note_id)
            if all_tags:
                await self._add_tags_to_note(note_id, list(all_tags))

            await self.session.refresh(updated_note, ["tags"])

        return await self._note_to_response(updated_note, user_id)

    async def delete_note(self, note_id: UUID, user_id: UUID) -> bool:
        """Delete note."""
        return await self.note_repo.delete_note(note_id, user_id)

    async def list_user_notes(
        self,
        user_id: UUID,
        page: int = 1,
        per_page: int = 20,
        tag_filter: Optional[List[str]] = None,
    ) -> NoteListResponse:
        """List user notes with pagination."""
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20

        notes, total_count = await self.note_repo.list_user_notes(
            user_id, page, per_page, tag_filter
        )

        note_responses = [await self._note_to_list_item(note, user_id) for note in notes]

        return NoteListResponse.create(
            items=note_responses, total=total_count, page=page, per_page=per_page
        )

    async def validate_hyperlinks(self, hyperlinks: List[str]) -> Dict[str, bool]:
        """Validate URLs in note content by checking accessibility."""
        import aiohttp

        url_pattern = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        )

        results = {}

        async with aiohttp.ClientSession() as session:
            for url in hyperlinks:
                # Basic URL format validation
                if not url_pattern.match(url):
                    results[url] = False
                    continue
                try:
                    async with session.get(url, timeout=5) as resp:
                        results[url] = resp.status == 200
                except Exception:
                    results[url] = False

        return results

    async def get_available_tags(self, user_id: UUID) -> List[str]:
        """Get all user tags."""
        return await self.note_repo.get_user_tags(user_id)

    def _extract_tags_from_content(self, content: str) -> List[str]:
        """Extract hashtags from note content."""
        hashtag_pattern = re.compile(r"#(\w+)")
        matches = hashtag_pattern.findall(content)
        return list(set(matches))  # Remove duplicates

    async def _add_tags_to_note(self, note_id: UUID, tag_names: List[str]):
        """Add tags to a note."""
        from sqlalchemy import and_, select

        from ..models.tag import NoteTag

        for tag_name in tag_names:
            # Check if tag exists
            tag_stmt = select(Tag).where(Tag.name == tag_name)
            tag_result = await self.session.execute(tag_stmt)
            tag = tag_result.scalar_one_or_none()

            if not tag:
                # Create new tag
                tag = Tag(name=tag_name)
                self.session.add(tag)
                await self.session.flush()

            # Check if association already exists
            existing_stmt = select(NoteTag).where(
                and_(NoteTag.note_id == note_id, NoteTag.tag_id == tag.id)
            )
            existing_result = await self.session.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if not existing:
                note_tag = NoteTag(note_id=note_id, tag_id=tag.id)
                self.session.add(note_tag)

        await self.session.commit()

    async def _clear_note_tags(self, note_id: UUID):
        """Remove all tags from a note."""
        from sqlalchemy import delete

        from ..models.tag import NoteTag

        # Delete all note-tag associations for this note
        stmt = delete(NoteTag).where(NoteTag.note_id == note_id)
        await self.session.execute(stmt)
        await self.session.commit()

    async def _note_to_response(self, note, current_user_id=None, override_tags=None, can_edit_override=None) -> NoteResponse:
        """Convert note model to response."""
        # Use override_tags if provided, otherwise try to load from relationship
        if override_tags is not None:
            tags = override_tags
        else:
            # Safe access to potentially lazy-loaded attributes
            tags = []
            if hasattr(note, "tags"):
                try:
                    tags = [tag.name for tag in note.tags] if note.tags else []
                except Exception:
                    tags = []  # Fallback if tags can't be loaded

        # Fetch owner information
        owner_info = await self._get_user_info(note.owner_id)
        owner_username = owner_info.username if owner_info else None
        owner_display_name = owner_info.full_name if owner_info else None

        return NoteResponse(
            id=note.id,
            title=note.title,
            content=note.content,
            tags=tags,
            hyperlinks=note.hyperlinks or [],
            is_public=getattr(note, "is_public", False),
            owner_id=note.owner_id,
            owner_username=owner_username,
            owner_display_name=owner_display_name,
            is_shared=current_user_id != note.owner_id if current_user_id else False,
            is_owned=current_user_id == note.owner_id if current_user_id else False,
            can_edit=can_edit_override if can_edit_override is not None else (current_user_id == note.owner_id if current_user_id else False),
            created_at=note.created_at,
            updated_at=note.updated_at,
            view_count=getattr(note, "view_count", 0),
            share_count=0,  # TODO: calculate actual share count
        )

    async def _note_to_list_item(self, note, current_user_id=None, override_tags=None) -> NoteListItem:
        """Convert note model to list item response."""
        # Use override_tags if provided, otherwise try to load from relationship
        if override_tags is not None:
            tags = override_tags
        else:
            # Safe access to potentially lazy-loaded attributes
            tags = []
            if hasattr(note, "tags"):
                try:
                    tags = [tag.name for tag in note.tags] if note.tags else []
                except:
                    tags = []  # Fallback if tags can't be loaded

        # Create content preview (first 200 chars)
        content = note.content or ""
        content_preview = content[:200]
        if len(content) > 200:
            content_preview += "..."

        # Fetch owner information
        owner_info = await self._get_user_info(note.owner_id)
        owner_username = owner_info.username if owner_info else None
        owner_display_name = owner_info.full_name if owner_info else None

        return NoteListItem(
            id=note.id,
            title=note.title,
            content_preview=content_preview,
            tags=tags,
            owner_id=note.owner_id,
            owner_username=owner_username,
            owner_display_name=owner_display_name,
            is_shared=current_user_id != note.owner_id if current_user_id else False,
            is_owned=current_user_id == note.owner_id if current_user_id else False,
            can_edit=current_user_id == note.owner_id if current_user_id else False,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )

    def _extract_hyperlinks_from_text(self, text: str) -> List[str]:
        """Extract hyperlinks from text content using regex."""
        import re

        url_pattern = r'https?://[^\s<>":' "'" "`|(){}[\]]*"
        urls = re.findall(url_pattern, text, re.IGNORECASE)
        return list(set(urls))

    async def _get_user_info(self, user_id: UUID) -> Optional[User]:
        """Get user information by ID."""
        return await self.user_repo.get_by_id(user_id)


def _get_or_create_tag_by_name(session: Session, name: str, created_by: User | None) -> Tag:
    norm = Tag.normalize_name(name)
    tag = session.query(Tag).filter_by(name=norm).one_or_none()
    if tag:
        return tag

    tag = Tag(name=norm, created_by_user_id=(created_by.id if created_by else None))
    session.add(tag)
    try:
        session.flush()  # forza INSERT per catturare UniqueConstraint race
        return tag
    except IntegrityError:
        session.rollback()
        # qualcun altro l'ha creato nel frattempo: ricarica
        return session.query(Tag).filter_by(name=norm).one()


def attach_tags_to_note(
    session: Session, note: Note, tag_names: Iterable[str], user: User | None
) -> list[Tag]:
    names = {Tag.normalize_name(n) for n in tag_names if Tag.normalize_name(n)}
    if not names:
        return []

    tags: list[Tag] = []
    for n in names:
        tag = _get_or_create_tag_by_name(session, n, user)
        # Evita duplicati di associazione (coperto anche da UniqueConstraint)
        already = any(nt.tag_id == tag.id for nt in note.note_tags)
        if not already:
            # Usa association object per valorizzare i metadati
            tag.note_tags.append(NoteTag(note=note, tagged_by_user_id=(user.id if user else None)))
        tags.append(tag)

    # opzionale: flush per materializzare gli INSERT in note_tags e aggiornare usage_count via eventi
    session.flush()
    return tags
