"""User repository for database operations."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, user_data: dict) -> User:
        """Create new user."""
        user = User(**user_data)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_user(self, user_id: UUID, update_data: dict) -> Optional[User]:
        """Update user data."""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        for key, value in update_data.items():
            setattr(user, key, value)

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete_user(self, user_id: UUID) -> bool:
        """Delete user."""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        await self.session.delete(user)
        await self.session.commit()
        return True

    async def is_username_taken(self, username: str) -> bool:
        """Check if username exists."""
        user = await self.get_by_username(username)
        return user is not None

    # Additional methods for test compatibility
    async def list_users(self, page: int = 1, per_page: int = 20) -> tuple[list[User], int]:
        """List all users with pagination."""
        from sqlalchemy import func

        offset = (page - 1) * per_page

        # Count query
        count_stmt = select(func.count(User.id))
        total_result = await self.session.execute(count_stmt)
        total_count = total_result.scalar()

        # Data query
        stmt = select(User).offset(offset).limit(per_page)
        result = await self.session.execute(stmt)
        users = list(result.scalars())

        return users, total_count

    async def check_username_exists(self, username: str) -> bool:
        """Alias for is_username_taken."""
        return await self.is_username_taken(username)
