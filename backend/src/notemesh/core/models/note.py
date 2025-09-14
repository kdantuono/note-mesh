"""Note model for user content."""
import uuid
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Text, Integer, Index, ForeignKey, CheckConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship, attributes as orm_attributes, validates
from pydantic import HttpUrl

from .base import BaseModel
from .types import HttpUrlListType, GUID

if TYPE_CHECKING:
    from .user import User
    from .tag import Tag, NoteTag
    from .share import Share


class Note(BaseModel):
    """Note with content and hyperlinks."""

    __tablename__ = "notes"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_public: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Store as list of URLs; on SQLite it's JSON TEXT via HttpUrlListType
    hyperlinks: Mapped[Optional[List[HttpUrl]]] = mapped_column(
        HttpUrlListType, nullable=True
    )

    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_viewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # owner reference
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="notes",
        doc="User who created and owns this note",
        lazy="selectin",
    )

    note_tags: Mapped[List["NoteTag"]] = relationship(
        "NoteTag",
        back_populates="note",
        # Rely on DB-level ON DELETE CASCADE to remove note_tags rows
        # Avoid ORM-managed delete-orphan which may lazy-load in sync context
        passive_deletes=True,
        doc="Tag associations for this note",
        lazy="selectin",
        overlaps="tags,notes",
    )

    shares: Mapped[List["Share"]] = relationship(
        "Share",
        back_populates="note",
        # Rely on DB-level ON DELETE CASCADE; avoid loading children during delete
        passive_deletes=True,
        doc="Share records granting access to other users",
        lazy="selectin",
    )

    # Many-to-many relationship with tags through note_tags
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary="note_tags",
        back_populates="notes",
        lazy="selectin",
        overlaps="note_tags",
        doc="Tags associated with this note",
    )

    # Database indexes and constraints
    __table_args__ = (
        # Full-text search indexes (basic btree on SQLite)
        Index("idx_notes_title_fts", "title"),
        Index("idx_notes_content_fts", "content"),

        # Query optimization indexes
        Index("idx_notes_owner_id", "owner_id"),
        Index("idx_notes_created_at", "created_at"),
        Index("idx_notes_view_count", "view_count"),
        Index("idx_notes_owner_created", "owner_id", "created_at"),
        Index("idx_notes_owner_view_count", "owner_id", "view_count"),

        # Enforce title max length (SQLite compatible)
        CheckConstraint("length(title) <= 200", name="ck_notes_title_len"),
    )

    def __repr__(self) -> str:
        """Return a string representation of the Note instance."""
        truncated = self.title if len(self.title) <= 30 else (self.title[:30] + "...")
        return f"<Note(title='{truncated}', owner_id={self.owner_id})>"

    @property
    def preview(self) -> str:
        """Get content preview (max 150 chars)."""
        if len(self.content) <= 150:
            return self.content
        return self.content[:147] + "..."

    @property
    def hyperlink_count(self) -> int:
        """Get the number of hyperlinks in this note."""
        return len(self.hyperlinks) if self.hyperlinks else 0

    @property
    def tag_names(self) -> List[str]:
        """Get list of tag names associated with this note."""
        return [note_tag.tag.name for note_tag in self.note_tags]

    def increment_view_count(self) -> None:
        """Increment the view count and update last viewed timestamp."""
        self.view_count += 1
        self.last_viewed_at = datetime.utcnow()

    def is_owned_by(self, user_id: uuid.UUID) -> bool:
        """Check if this note is owned by the specified user."""
        return self.owner_id == user_id

    def extract_hyperlinks_from_content(self) -> List[str]:
        """Extract potential hyperlinks from note content using regex."""
        import re

        url_pattern = r'https?://[^\s<>":'"'"'`|(){}[\]]*'
        urls = re.findall(url_pattern, self.content, re.IGNORECASE)
        return list(set(urls))

    @validates("hyperlinks")
    def _validate_hyperlinks(self, key, value):  # noqa: ARG002
        """Ensure each hyperlink is at most 500 characters."""
        if value is None:
            return value
        links = [str(v) for v in value]
        if any(len(link) > 500 for link in links):
            raise ValueError("Each hyperlink must be at most 500 characters long")
        return links


# Ensure relationship collections are initialized to avoid implicit lazy loads
@event.listens_for(Note, "init", propagate=True)
def _init_note_collections(target, args, kwargs):
    # Only set if not provided explicitly
    if "tags" not in kwargs:
        orm_attributes.set_committed_value(target, "tags", [])
    if "note_tags" not in kwargs:
        orm_attributes.set_committed_value(target, "note_tags", [])
    if "shares" not in kwargs:
        orm_attributes.set_committed_value(target, "shares", [])