"""Custom SQLAlchemy types for NoteMesh models with cross-DB support."""

import json
import uuid
from typing import List, Optional

from sqlalchemy import String, Text, TypeDecorator


class HttpUrlListType(TypeDecorator):
    """
    Store a list of URL strings in a DB-friendly way:

    - On PostgreSQL: uses ARRAY(String(500))
    - On SQLite (and others): stores JSON text in a TEXT column

    Always returns List[str] to keep model layer simple and test-friendly.
    """

    cache_ok = True
    impl = Text  # placeholder, real impl decided per-dialect

    def load_dialect_impl(self, dialect):
        # Choose storage strategy based on dialect
        if dialect.name == "postgresql":
            from sqlalchemy import String as SAString
            from sqlalchemy.dialects.postgresql import ARRAY

            return dialect.type_descriptor(ARRAY(SAString(500)))
        # Fallback (e.g., sqlite): JSON as TEXT
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Optional[List[str]], dialect):
        if value is None:
            return None
        # Normalize to list of strings
        values = [str(v) for v in value]
        if dialect.name == "postgresql":
            return values
        # JSON encode for TEXT storage
        return json.dumps(values)

    def process_result_value(self, value, dialect) -> Optional[List[str]]:
        if value is None:
            return None
        if dialect.name == "postgresql":
            # Ensure elements are strings
            return [str(v) for v in value]
        # Decode JSON from TEXT
        try:
            return [str(v) for v in json.loads(value)]
        except Exception:
            # In case DB already returns a list (unlikely on SQLite)
            return [str(v) for v in value] if isinstance(value, list) else None


class GUID(TypeDecorator):
    """
    Platform-independent GUID/UUID type.

    - Uses PostgreSQL UUID type when available
    - Falls back to CHAR(36) storing hex string form on other DBs (e.g., SQLite)
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID

            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # PostgreSQL expects uuid.UUID when as_uuid=True, others expect string
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            # Already a uuid.UUID from PG when as_uuid=True
            return value
        # Coerce string back to uuid.UUID for SQLite/others
        try:
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        except Exception:
            return value
