# Note sharing between users
import uuid
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import String, DateTime, Index, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .user import User
    from .note import Note


class ShareStatus(str, Enum):
    """Share status options."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


class Share(BaseModel):
    """Share notes with other users (read-only)."""

    __tablename__ = "shares"

    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    shared_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    shared_with_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Permission level for this share (read/write)
    permission: Mapped[str] = mapped_column(
        String(20), default="read", nullable=False
    )

    status: Mapped[ShareStatus] = mapped_column(
        String(20), default=ShareStatus.ACTIVE, nullable=False
    )

    shared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    access_count: Mapped[int] = mapped_column(default=0, nullable=False)
    share_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    note: Mapped["Note"] = relationship("Note", back_populates="shares")
    shared_by_user: Mapped["User"] = relationship("User", foreign_keys=[shared_by_user_id], back_populates="shares_given")
    shared_with_user: Mapped["User"] = relationship("User", foreign_keys=[shared_with_user_id], back_populates="shares_received")

    __table_args__ = (
        UniqueConstraint("note_id", "shared_with_user_id", name="uq_shares_note_recipient"),
        # Enforce length constraints
        CheckConstraint("length(permission) <= 20", name="ck_shares_permission_len"),
        CheckConstraint("length(status) <= 20", name="ck_shares_status_len"),
        CheckConstraint("share_message IS NULL OR length(share_message) <= 500", name="ck_shares_message_len"),
        Index("idx_shares_note_id", "note_id"),
        Index("idx_shares_shared_by", "shared_by_user_id"),
        Index("idx_shares_shared_with", "shared_with_user_id"),
        Index("idx_shares_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Share(note_id={self.note_id}, shared_with={self.shared_with_user_id}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if share is active and not expired."""
        if self.status != ShareStatus.ACTIVE:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    @property
    def is_expired(self) -> bool:
        """Check if expired."""
        return self.expires_at is not None and datetime.utcnow() > self.expires_at

    def record_access(self) -> None:
        """Track when someone accessed the shared note."""
        self.access_count += 1
        self.last_accessed_at = datetime.utcnow()

    def revoke(self) -> None:
        """Revoke access."""
        self.status = ShareStatus.REVOKED

    def check_permission(self, user_id: uuid.UUID) -> dict[str, bool]:
        """Check what user can do with this share."""
        return {
            "can_read": (user_id == self.shared_with_user_id and self.is_active) or user_id == self.shared_by_user_id,
            "can_edit": user_id == self.shared_by_user_id,  # only owner edits
            "is_owner": user_id == self.shared_by_user_id,
            "is_recipient": user_id == self.shared_with_user_id,
        }