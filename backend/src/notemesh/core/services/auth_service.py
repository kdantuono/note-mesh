"""Authentication service implementation."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .interfaces import IAuthService
from ..repositories.user_repository import UserRepository
from ..repositories.refresh_token_repository import RefreshTokenRepository
from ..schemas.auth import (
    LoginRequest, TokenResponse, RegisterRequest, UserResponse,
    RefreshTokenRequest, PasswordChangeRequest, UserUpdateRequest
)
from ...security import hash_password, verify_password, create_access_token, create_refresh_token
from ...config import get_settings


class AuthService(IAuthService):
    """Authentication service implementation."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.token_repo = RefreshTokenRepository(session)
        self.settings = get_settings()

    async def register_user(self, request: RegisterRequest) -> UserResponse:
        """Register new user."""
        # Check if username already exists
        if await self.user_repo.is_username_taken(request.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

        # Hash password
        hashed_password = hash_password(request.password)

        # Create user
        user_data = {
            "username": request.username,
            "password_hash": hashed_password,
            "full_name": request.full_name,
            "is_active": True,
            "is_verified": True
        }

        user = await self.user_repo.create_user(user_data)

        return UserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    async def authenticate_user(self, request: LoginRequest) -> TokenResponse:
        """Login user and return JWT tokens."""
        # Get user by username
        user = await self.user_repo.get_by_username(request.username)
        if not user or not user.can_login():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Verify password
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Create tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token()

        # Store refresh token
        token_data = {
            "token": refresh_token,
            "user_id": user.id,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=self.settings.refresh_token_expire_days)
        }
        await self.token_repo.create_token(token_data)

        # Create user response
        user_response = UserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.settings.access_token_expire_minutes * 60,
            user=user_response
        )

    async def refresh_token(self, request: RefreshTokenRequest) -> TokenResponse:
        """Refresh JWT token."""
        # Validate refresh token
        if not await self.token_repo.is_token_valid(request.refresh_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Get token and user
        token_obj = await self.token_repo.get_by_token(request.refresh_token)
        if not token_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        user = await self.user_repo.get_by_id(token_obj.user_id)
        if not user or not user.can_login():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account inactive"
            )

        # Create new access token
        access_token = create_access_token(data={"sub": str(user.id)})

        # Create new refresh token
        new_refresh_token = create_refresh_token()

        # Delete old refresh token and create new one
        await self.token_repo.delete_token(request.refresh_token)
        token_data = {
            "token": new_refresh_token,
            "user_id": user.id,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=self.settings.refresh_token_expire_days)
        }
        await self.token_repo.create_token(token_data)

        # Create user response
        user_response = UserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=self.settings.access_token_expire_minutes * 60,
            user=user_response
        )

    async def get_current_user(self, user_id: UUID) -> UserResponse:
        """Get user by ID."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    async def update_user_profile(self, user_id: UUID, request: UserUpdateRequest) -> UserResponse:
        """Update user profile."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if new username is available (if changing)
        if request.username and request.username != user.username:
            if await self.user_repo.is_username_taken(request.username):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )

        # Update user data
        update_data = {}
        if request.username:
            update_data["username"] = request.username
        if request.full_name is not None:
            update_data["full_name"] = request.full_name

        if update_data:
            user = await self.user_repo.update_user(user_id, update_data)

        return UserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    async def change_password(self, user_id: UUID, request: PasswordChangeRequest) -> bool:
        """Change user password."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify current password
        if not verify_password(request.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Hash new password
        new_hash = hash_password(request.new_password)
        await self.user_repo.update_user(user_id, {"password_hash": new_hash})

        # Revoke all refresh tokens for security
        await self.token_repo.delete_user_tokens(user_id)

        return True

    async def logout_user(self, user_id: UUID, access_token: str) -> bool:
        """Logout user."""
        # Delete all refresh tokens for user
        deleted_count = await self.token_repo.delete_user_tokens(user_id)
        return deleted_count > 0