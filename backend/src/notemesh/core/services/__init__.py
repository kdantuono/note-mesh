"""
Service layer interfaces and implementations.

Following the TOP-DOWN approach, this module defines service interfaces
first, then concrete implementations with TODO markers for bottom-up development.
"""

from .auth_service import AuthService
from .health_service import HealthService
from .interfaces import IAuthService, IHealthService, INoteService, ISearchService, ISharingService
from .note_service import NoteService
from .search_service import SearchService
from .sharing_service import SharingService

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
