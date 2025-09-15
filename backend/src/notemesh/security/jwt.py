"""JWT token utilities."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from jose import JWTError, jwt

from ..config import get_settings
from ..core.redis_client import get_redis_client


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with JTI for Redis blacklisting."""
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    # Add JWT ID for blacklisting capability
    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "type": "access", "jti": jti})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token() -> str:
    """Create a random refresh token."""
    return secrets.token_urlsafe(32)


async def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate access token, checking Redis blacklist."""
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # Verify token type
        if payload.get("type") != "access":
            return None

        # Check if token is blacklisted in Redis
        jti = payload.get("jti")
        if jti:
            redis_client = get_redis_client()
            try:
                await redis_client.connect()  # Ensure connection
                is_blacklisted = await redis_client.is_token_blacklisted(jti)
                if is_blacklisted:
                    return None
            except Exception:
                # If Redis is down, allow token validation to continue
                pass

        return payload
    except JWTError:
        return None


async def get_user_id_from_token(token: str) -> Optional[UUID]:
    """Extract user ID from token."""
    payload = await decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        return UUID(user_id)
    except ValueError:
        return None


async def blacklist_token(token: str) -> bool:
    """Add token to Redis blacklist for secure logout."""
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        jti = payload.get("jti")

        if not jti:
            return False

        # Calculate remaining TTL for the token
        exp = payload.get("exp")
        if exp:
            expire_time = datetime.fromtimestamp(exp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            remaining_seconds = int((expire_time - now).total_seconds())

            if remaining_seconds > 0:
                redis_client = get_redis_client()
                await redis_client.connect()  # Ensure connection
                return await redis_client.add_to_blacklist(jti, remaining_seconds)

        return False
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Blacklist token error: {e}")
        return False
