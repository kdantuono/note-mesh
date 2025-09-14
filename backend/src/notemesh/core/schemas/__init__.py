"""
Pydantic schemas for validating and documenting API requests and responses.

This package exposes the Pydantic models used across the application to
define input/output contracts for authentication, notes, sharing, and
common responses (pagination and error formats).
"""

from .auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from .common import ErrorResponse, PaginationResponse
from .notes import (
    NoteCreate,
    NoteListResponse,
    NoteResponse,
    NoteSearchRequest,
    NoteSearchResponse,
    NoteUpdate,
)
from .sharing import SharedNoteResponse, ShareRequest, ShareResponse

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
