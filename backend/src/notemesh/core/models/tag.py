# Tag models for organizing notes
import uuid
from typing import List, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Integer, Index, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .note import Note


class Tag(BaseModel):
    """Tag for categorizing notes."""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # hex colors

    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    note_tags: Mapped[List["NoteTag"]] = relationship(
        "NoteTag", back_populates="tag", cascade="all, delete-orphan"
    )

    created_by_user: Mapped["User"] = relationship("User")

    # Many-to-many relationship with notes through note_tags
    notes: Mapped[List["Note"]] = relationship(
        "Note",
        secondary="note_tags",
        back_populates="tags",
        doc="Notes that have this tag"
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_tags_name"),
        Index("idx_tags_name", "name"),
        Index("idx_tags_usage_count", "usage_count"),
        Index("idx_tags_created_by", "created_by_user_id"),
    )

    def __repr__(self) -> str:
        return f"<Tag(name='{self.name}', usage={self.usage_count})>"

    @classmethod
    def normalize_name(cls, name: str) -> str:
        """Clean up tag name."""
        clean = name.strip().lower()
        if not clean:
            raise ValueError("Tag name cannot be empty")
        return clean

    def increment_usage(self) -> None:
        """Add one to usage count."""
        self.usage_count += 1

    def decrement_usage(self) -> None:
        """Remove one from usage count."""
        self.usage_count = max(0, self.usage_count - 1)

    @property
    def is_popular(self) -> bool:
        """Check if tag is popular (10+ uses)."""
        return self.usage_count >= 10


class NoteTag(BaseModel):
    """Links notes to tags."""

    __tablename__ = "note_tags"

    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )

    tagged_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    tagged_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    note: Mapped["Note"] = relationship("Note", back_populates="note_tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="note_tags")
    tagged_by_user: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint("note_id", "tag_id", name="uq_note_tags_note_tag"),
        Index("idx_note_tags_note_id", "note_id"),
        Index("idx_note_tags_tag_id", "tag_id"),
        Index("idx_note_tags_user_id", "tagged_by_user_id"),
    )

    def __repr__(self) -> str:
        return f"<NoteTag(note_id={self.note_id}, tag_id={self.tag_id})>"