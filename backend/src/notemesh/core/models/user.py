"""
User model for authentication.
"""

import uuid
from typing import List, TYPE_CHECKING

from sqlalchemy import Boolean, String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .note import Note
    from .share import Share
    from .refresh_token import RefreshToken


class User(BaseModel):
    """User account model with username/password auth."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relations
    notes: Mapped[List["Note"]] = relationship("Note", back_populates="owner", cascade="all, delete-orphan")

    shares_given: Mapped[List["Share"]] = relationship("Share", foreign_keys="Share.shared_by_user_id", back_populates="shared_by_user", cascade="all, delete-orphan")
    shares_received: Mapped[List["Share"]] = relationship("Share", foreign_keys="Share.shared_with_user_id", back_populates="shared_with_user")

    refresh_tokens: Mapped[List["RefreshToken"]] = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_users_username", "username"),
        Index("idx_users_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User(username='{self.username}')>"

    @property
    def display_name(self) -> str:
        """Get display name."""
        return self.full_name if self.full_name else self.username

    def can_login(self) -> bool:
        """Check if user can login."""
        return self.is_active and self.is_verified

    def get_owned_note_ids(self) -> List[uuid.UUID]:
        """Get IDs of notes owned by this user."""
        return [note.id for note in self.notes]