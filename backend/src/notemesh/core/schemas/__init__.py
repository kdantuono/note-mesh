"""
Pydantic schemas for validating and documenting API requests and responses.

This package exposes the Pydantic models used across the application to
define input/output contracts for authentication, notes, sharing, and
common responses (pagination and error formats).
"""

from .auth import LoginRequest, TokenResponse, RegisterRequest, UserResponse
from .notes import (
    NoteCreate,
    NoteUpdate, 
    NoteResponse,
    NoteListResponse,
    NoteSearchRequest,
    NoteSearchResponse
)
from .sharing import ShareRequest, ShareResponse, SharedNoteResponse
from .common import PaginationResponse, ErrorResponse

__all__ = [
    # Auth schemas
    "LoginRequest",
    "TokenResponse", 
    "RegisterRequest",
    "UserResponse",
    
    # Note schemas
    "NoteCreate",
    "NoteUpdate",
    "NoteResponse", 
    "NoteListResponse",
    "NoteSearchRequest",
    "NoteSearchResponse",
    
    # Sharing schemas
    "ShareRequest",
    "ShareResponse",
    "SharedNoteResponse",
    
    # Common schemas
    "PaginationResponse",
    "ErrorResponse",
]