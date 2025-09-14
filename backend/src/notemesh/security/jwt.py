"""JWT token utilities."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from jose import JWTError, jwt

from ..config import get_settings


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token() -> str:
    """Create a random refresh token."""
    return secrets.token_urlsafe(32)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate access token."""
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # Verify token type
        if payload.get("type") != "access":
            return None

        return payload
    except JWTError:
        return None


def get_user_id_from_token(token: str) -> Optional[UUID]:
    """Extract user ID from token."""
    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        return UUID(user_id)
    except ValueError:
        return None
