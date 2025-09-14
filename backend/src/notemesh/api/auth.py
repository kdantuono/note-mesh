"""Authentication API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
)
from ..core.services import AuthService
from ..database import get_db_session
from ..middleware.auth import get_current_user_id

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_db_session)):
    """Register a new user."""
    auth_service = AuthService(session)
    return await auth_service.register_user(request)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, session: AsyncSession = Depends(get_db_session)):
    """Login user and get JWT tokens."""
    auth_service = AuthService(session)
    return await auth_service.authenticate_user(request)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest, session: AsyncSession = Depends(get_db_session)
):
    """Refresh JWT token using refresh token."""
    auth_service = AuthService(session)
    return await auth_service.refresh_token(request)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Get current user profile."""
    auth_service = AuthService(session)
    return await auth_service.get_current_user(current_user_id)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    request: UserUpdateRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Update user profile."""
    auth_service = AuthService(session)
    return await auth_service.update_user_profile(current_user_id, request)


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    request: PasswordChangeRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Change user password."""
    auth_service = AuthService(session)
    success = await auth_service.change_password(current_user_id, request)
    if success:
        return {"message": "Password changed successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to change password"
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Logout user (revoke all refresh tokens)."""
    auth_service = AuthService(session)
    success = await auth_service.logout_user(
        current_user_id, ""
    )  # Access token not needed for this implementation
    if success:
        return {"message": "Logged out successfully"}
    else:
        return {"message": "No active sessions found"}
