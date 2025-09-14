"""API routers for NoteMesh."""

from .auth import router as auth_router
from .health import router as health_router
from .notes import router as notes_router
from .search import router as search_router
from .sharing import router as sharing_router

__all__ = ["auth_router", "notes_router", "search_router", "sharing_router", "health_router"]
