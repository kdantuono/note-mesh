"""
Auth schemas for login/register stuff
"""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    remember_me: bool = Field(default=False)
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "mario85",
                "password": "mypass123",
                "remember_me": False
            }
        }


class RegisterRequest(BaseModel):
    # basic registration fields
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=100)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
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
                "username": "paperino",
                "password": "paperino123!",
                "confirm_password": "paperino123!",
                "full_name": "Rino detto Paperino"
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
                "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "username": "mario_writer",
                "full_name": "Mario Bianchi",
                "is_active": True,
                "created_at": "2025-08-15T14:22:33Z",
                "updated_at": "2025-09-12T09:14:07Z",
                "notes_count": 17,
                "shared_notes_count": 3
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