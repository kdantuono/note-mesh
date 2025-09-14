"""Custom SQLAlchemy types for NoteMesh models."""

from typing import List, Optional
from sqlalchemy import TypeDecorator, String
from sqlalchemy.dialects.postgresql import ARRAY
from pydantic import HttpUrl
import json


class HttpUrlListType(TypeDecorator):
    """Custom SQLAlchemy type that stores List[HttpUrl] as List[String] in PostgreSQL."""

    impl = ARRAY(String(500))
    cache_ok = True

    def process_bind_param(self, value: Optional[List[HttpUrl]], dialect) -> Optional[List[str]]:
        """Convert List[HttpUrl] to List[str] when storing to database."""
        if value is None:
            return None
        return [str(url) for url in value]

    def process_result_value(self, value: Optional[List[str]], dialect) -> Optional[List[HttpUrl]]:
        """Convert List[str] to List[HttpUrl] when reading from database."""
        if value is None:
            return None
        return [HttpUrl(url) for url in value]