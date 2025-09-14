"""Refresh token repository for database operations."""

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Repository for refresh token database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_token(self, token_data: dict) -> RefreshToken:
        """Create new refresh token."""
        token = RefreshToken(**token_data)
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def get_by_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token by token string."""
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_token(self, user_id: UUID, token: str) -> Optional[RefreshToken]:
        """Get refresh token for specific user."""
        stmt = select(RefreshToken).where(
            and_(RefreshToken.user_id == user_id, RefreshToken.token == token)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_token(self, token: str) -> bool:
        """Delete specific refresh token."""
        token_obj = await self.get_by_token(token)
        if not token_obj:
            return False

        await self.session.delete(token_obj)
        await self.session.commit()
        return True

    async def delete_user_tokens(self, user_id: UUID) -> int:
        """Delete all refresh tokens for user."""
        stmt = delete(RefreshToken).where(RefreshToken.user_id == user_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def delete_expired_tokens(self) -> int:
        """Delete all expired tokens."""
        now = datetime.now(timezone.utc)
        stmt = delete(RefreshToken).where(RefreshToken.expires_at < now)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def is_token_valid(self, token: str) -> bool:
        """Check if token exists and is not expired."""
        token_obj = await self.get_by_token(token)
        if not token_obj:
            return False

        return token_obj.expires_at > datetime.now(timezone.utc) and token_obj.is_active