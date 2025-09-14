"""
Service layer interfaces and implementations.

Following the TOP-DOWN approach, this module defines service interfaces
first, then concrete implementations with TODO markers for bottom-up development.
"""

from .interfaces import (
    IAuthService,
    INoteService, 
    ISearchService,
    ISharingService,
    IHealthService
)

from .auth_service import AuthService
from .note_service import NoteService
from .search_service import SearchService
from .sharing_service import SharingService
from .health_service import HealthService

__all__ = [
    # Interfaces
    "IAuthService",
    "INoteService",
    "ISearchService", 
    "ISharingService",
    "IHealthService",
    
    # Implementations
    "AuthService",
    "NoteService",
    "SearchService",
    "SharingService", 
    "HealthService",
]