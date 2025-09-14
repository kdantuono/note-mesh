# Note model for user content
import uuid
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Text, Integer, Index, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import event
from sqlalchemy.orm import attributes as orm_attributes
from pydantic import HttpUrl

from .base import BaseModel
from .types import HttpUrlListType

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

    hyperlinks: Mapped[Optional[List[HttpUrl]]] = mapped_column(HttpUrlListType, nullable=True) # links in content

    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_viewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # owner reference
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="notes",
        doc="User who created and owns this note"
    )

    note_tags: Mapped[List["NoteTag"]] = relationship(
        "NoteTag",
        back_populates="note",
        cascade="all, delete-orphan",
        doc="Tag associations for this note"
    )

    shares: Mapped[List["Share"]] = relationship(
        "Share",
        back_populates="note",
        cascade="all, delete-orphan",
        doc="Share records granting access to other users"
    )

    # Many-to-many relationship with tags through note_tags
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary="note_tags",
        back_populates="notes",
        lazy="selectin",
        overlaps="note_tags",
        doc="Tags associated with this note"
    )


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

    # Database indexes for performance
    __table_args__ = (
        # Full-text search indexes
        Index("idx_notes_title_fts", "title"),
        Index("idx_notes_content_fts", "content"),

        # Query optimization indexes
        Index("idx_notes_owner_id", "owner_id"),
        Index("idx_notes_created_at", "created_at"),
        Index("idx_notes_view_count", "view_count"),
        Index("idx_notes_owner_created", "owner_id", "created_at"),

        # Composite index for user note listing with sorting
        Index("idx_notes_owner_view_count", "owner_id", "view_count"),
        # Enforce title max length (SQLite compatible)
        CheckConstraint("length(title) <= 200", name="ck_notes_title_len"),
    )

    def __repr__(self) -> str:
        """
        Return a string representation of the Note instance.

        Returns:
            str: String representation showing title and owner
        """
        # Tests expect a truncated title at 30 characters plus an ellipsis
        truncated = self.title if len(self.title) <= 30 else (self.title[:30] + "...")
        return f"<Note(title='{truncated}', owner_id={self.owner_id})>"

    @property
    def preview(self) -> str:
        """Get content preview."""
        if len(self.content) <= 150:
            return self.content
        return self.content[:147] + "..."

    @property
    def hyperlink_count(self) -> int:
        """
        Get the number of hyperlinks in this note.

        Returns:
            int: Count of hyperlinks, 0 if none exist
        """
        return len(self.hyperlinks) if self.hyperlinks else 0

    @property
    def tag_names(self) -> List[str]:
        """
        Get list of tag names associated with this note.

        Utility method to quickly access tag names without loading
        full Tag objects. Useful for API responses and search indexing.

        Returns:
            List[str]: List of tag names, empty list if no tags

        Note:
            This method assumes note_tags relationship is loaded.
            For performance, consider using a specific query if
            tag data is not needed elsewhere.
        """
        return [note_tag.tag.name for note_tag in self.note_tags]

    def increment_view_count(self) -> None:
        """
        Increment the view count and update last viewed timestamp.

        Should be called whenever this note is accessed by any user.
        Used for analytics and trending calculations.

        Side Effects:
            - Increases view_count by 1
            - Sets last_viewed_at to current UTC time
            - Changes are pending until session is committed
        """
        self.view_count += 1
        self.last_viewed_at = datetime.utcnow()

    def is_owned_by(self, user_id: uuid.UUID) -> bool:
        """
        Check if this note is owned by the specified user.

        Utility method for permission checking in service layers.

        Args:
            user_id: UUID of user to check ownership against

        Returns:
            bool: True if user owns this note, False otherwise
        """
        return self.owner_id == user_id

    def extract_hyperlinks_from_content(self) -> List[str]:
        """
        Extract potential hyperlinks from note content.

        Scans the note content for URLs using basic pattern matching.
        This is a utility method for validation services that need to
        identify and validate hyperlinks before storage.

        Returns:
            List[str]: List of potential URLs found in content

        Note:
            This method uses basic regex patterns and may not catch all
            edge cases. Consider using a more robust URL extraction library
            for production use.
        """
        import re

        # Simple URL pattern matching
        url_pattern = r'https?://[^\s<>"\'`|(){}[\]]*'
        urls = re.findall(url_pattern, self.content, re.IGNORECASE)

        return list(set(urls))  # Remove duplicates