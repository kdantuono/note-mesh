# Base model for database stuff
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .types import GUID


class BaseModel(DeclarativeBase):
    """Common base for all models."""

    __abstract__ = True

    # using UUIDs everywhere
    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"

    def __eq__(self, other: object) -> bool:
        """Equality by primary key if available and same mapped class.

        This helps tests compare ORM instances representing the same row
        even if they're different Python objects (e.g., after refresh/query).
        """
        if self is other:
            return True
        if not isinstance(other, self.__class__):
            return NotImplemented  # type: ignore[return-value]
        try:
            return getattr(self, "id", None) is not None and self.id == other.id  # type: ignore[attr-defined]
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON."""
        result = {}
        for column in self.__table__.columns:
            val = getattr(self, column.name)
            if isinstance(val, uuid.UUID):
                val = str(val)
            elif isinstance(val, datetime):
                val = val.isoformat()
            result[column.name] = val
        return result
