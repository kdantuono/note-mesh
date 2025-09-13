# JWT refresh tokens
import uuid
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import secrets

from sqlalchemy import String, Boolean, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .user import User


class RefreshToken(BaseModel):
    """Refresh token for JWT auth."""

    __tablename__ = "refresh_tokens"

    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    device_identifier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    token_family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, default=uuid.uuid4
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_from_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 support
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("idx_refresh_tokens_token", "token"),
        Index("idx_refresh_tokens_user_id", "user_id"),
        Index("idx_refresh_tokens_is_active", "is_active"),
        Index("idx_refresh_tokens_expires_at", "expires_at"),
        Index("idx_refresh_tokens_user_active", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        token_preview = f"{self.token[:8]}..." if self.token else "None"
        return f"<RefreshToken(user_id={self.user_id}, token={token_preview}, active={self.is_active})>"

    @classmethod
    def generate_secure_token(cls) -> str:
        """Generate cryptographically secure token."""
        return secrets.token_urlsafe(24)  # 192-bit token

    @classmethod
    def create_for_user(cls, user_id: uuid.UUID, device_id: Optional[str] = None,
                       ip: Optional[str] = None, expires_days: int = 7) -> "RefreshToken":
        """Create new refresh token for user."""
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
        return cls(
            token=cls.generate_secure_token(),
            user_id=user_id,
            device_identifier=device_id,
            created_from_ip=ip,
            expires_at=expires_at,
            token_family_id=uuid.uuid4()
        )

    @property
    def is_expired(self) -> bool:
        """Check if token expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return self.is_active and not self.is_expired

    def record_usage(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.utcnow()

    def revoke(self, reason: str = "manual") -> None:
        """Revoke this token."""
        self.is_active = False
        self.revoked_at = datetime.utcnow()
        self.revocation_reason = reason