"""
Authentication and authorization schemas.

These schemas define the API contracts for user authentication,
registration, and JWT token management.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid


class LoginRequest(BaseModel):
    """User login request schema."""
    
    username: str = Field(min_length=3, max_length=50, description="Username")
    password: str = Field(min_length=8, max_length=128, description="User password")
    remember_me: bool = Field(default=False, description="Whether to extend session duration")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "securepassword123",
                "remember_me": False
            }
        }


class RegisterRequest(BaseModel):
    """User registration request schema."""
    
    username: str = Field(min_length=3, max_length=50, description="Unique username")
    password: str = Field(min_length=8, max_length=128, description="User password")
    confirm_password: str = Field(min_length=8, max_length=128, description="Password confirmation")
    full_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Full name (optional)"
    )
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        """Validate that passwords match."""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if v is not None:
            if not v.replace('_', '').replace('-', '').isalnum():
                raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "new_user",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
                "full_name": "New User"
            }
        }


class TokenResponse(BaseModel):
    """JWT token response schema."""
    
    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration time in seconds")
    user: "UserResponse" = Field(description="User information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 900,
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "user123",
                    "full_name": "User Name",
                    "is_active": True,
                    "created_at": "2025-09-13T10:30:00Z"
                }
            }
        }


class UserResponse(BaseModel):
    """User information response schema."""
    
    id: uuid.UUID = Field(description="User unique identifier")
    username: str = Field(description="Username")
    full_name: Optional[str] = Field(description="Full name")
    is_active: bool = Field(description="Whether user account is active")
    created_at: datetime = Field(description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(description="Last update timestamp")
    
    # Statistics (TODO: implement in service layer)
    notes_count: Optional[int] = Field(default=None, description="Total number of notes")
    shared_notes_count: Optional[int] = Field(default=None, description="Number of shared notes")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "pippo",
                "full_name": "Pippo The Ippo",
                "is_active": True,
                "created_at": "2025-09-13T10:30:00Z",
                "updated_at": "2025-09-13T11:00:00Z",
                "notes_count": 25,
                "shared_notes_count": 5
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    
    refresh_token: str = Field(description="JWT refresh token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""
    
    current_password: str = Field(description="Current password")
    new_password: str = Field(min_length=8, max_length=128, description="New password")
    confirm_new_password: str = Field(min_length=8, max_length=128, description="New password confirmation")
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        """Validate that new passwords match."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "oldpassword123",
                "new_password": "newsecurepassword123",
                "confirm_new_password": "newsecurepassword123"
            }
        }


class UserUpdateRequest(BaseModel):
    """User profile update request schema."""
    
    username: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=50,
        description="Username"
    )
    full_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Full name"
    )
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if v is not None:
            if not v.replace('_', '').replace('-', '').isalnum():
                raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "newusername",
                "full_name": "New Full Name"
            }
        }


# Forward reference resolution
TokenResponse.model_rebuild()