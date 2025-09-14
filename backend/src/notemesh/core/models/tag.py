# Tag models for organizing notes
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import attributes as orm_attributes
from sqlalchemy.orm import mapped_column, relationship

from .base import BaseModel
from .types import GUID

if TYPE_CHECKING:
    from .note import Note
    from .user import User


class Tag(BaseModel):
    """Tag for categorizing notes."""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # hex colors

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    note_tags: Mapped[List["NoteTag"]] = relationship(
        "NoteTag",
        back_populates="tag",
        cascade="all, delete-orphan",
        lazy="selectin",
        overlaps="notes,tags",
    )

    created_by_user: Mapped[Optional["User"]] = relationship("User", lazy="selectin")

    # Many-to-many relationship with notes through note_tags
    notes: Mapped[List["Note"]] = relationship(
        "Note",
        secondary="note_tags",
        back_populates="tags",
        lazy="selectin",
        overlaps="note_tags",
        doc="Notes that have this tag",
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_tags_name"),
        CheckConstraint("name = lower(name)", name="ck_tags_name_lowercase"),
        # Enforce max lengths at DB level even on SQLite
        CheckConstraint("length(name) <= 50", name="ck_tags_name_len"),
        CheckConstraint(
            "description IS NULL OR length(description) <= 200", name="ck_tags_description_len"
        ),
        CheckConstraint("color IS NULL OR length(color) <= 7", name="ck_tags_color_len"),
        Index("idx_tags_name", "name"),
        Index("idx_tags_usage_count", "usage_count"),
        Index("idx_tags_created_by", "created_by_user_id"),
    )

    def __repr__(self) -> str:
        return f"<Tag(name='{self.name}')>"

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


# Normalizza sempre il nome prima di INSERT/UPDATE
@event.listens_for(Tag, "before_insert", propagate=True)
def _normalize_tag_name_before_insert(mapper, connection, target: Tag):
    target.name = Tag.normalize_name(target.name)


@event.listens_for(Tag, "before_update", propagate=True)
def _normalize_tag_name_before_update(mapper, connection, target: Tag):
    target.name = Tag.normalize_name(target.name)


class NoteTag(BaseModel):
    """Links notes to tags."""

    __tablename__ = "note_tags"

    note_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )

    tagged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    tagged_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Relationships
    note: Mapped["Note"] = relationship(
        "Note", back_populates="note_tags", overlaps="tags,notes", lazy="selectin"
    )
    tag: Mapped["Tag"] = relationship(
        "Tag", back_populates="note_tags", overlaps="tags,notes", lazy="selectin"
    )
    tagged_by_user: Mapped[Optional["User"]] = relationship("User", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("note_id", "tag_id", name="uq_note_tags_note_tag"),
        Index("idx_note_tags_note_id", "note_id"),
        Index("idx_note_tags_tag_id", "tag_id"),
        Index("idx_note_tags_user_id", "tagged_by_user_id"),
    )

    def __repr__(self) -> str:
        return f"<NoteTag(note_id={self.note_id}, tag_id={self.tag_id})>"


# Mantieni usage_count coerente quando si aggiungono/rimuovono associazioni
@event.listens_for(Tag.note_tags, "append")
def _tag_usage_on_append(tag: Tag, note_tag: "NoteTag", initiator):
    tag.usage_count = (tag.usage_count or 0) + 1


@event.listens_for(Tag.note_tags, "remove")
def _tag_usage_on_remove(tag: Tag, note_tag: "NoteTag", initiator):
    tag.usage_count = max(0, (tag.usage_count or 0) - 1)


# Initialize Tag relationship collections to avoid accidental lazy-load on first access
@event.listens_for(Tag, "init", propagate=True)
def _init_tag_collections(target, args, kwargs):
    if "notes" not in kwargs:
        orm_attributes.set_committed_value(target, "notes", [])
    if "note_tags" not in kwargs:
        orm_attributes.set_committed_value(target, "note_tags", [])
