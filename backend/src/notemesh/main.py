# Main application entry point
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth_router, health_router, notes_router, search_router, sharing_router
from .config import get_settings
from .core.logging import LoggingMiddleware, get_logger, setup_logging
from .core.redis_client import get_redis_client
from .database import create_tables

# Setup logging first
setup_logging()
logger = get_logger("main")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(
        "Starting NoteMesh application",
        extra={"version": "0.1.0", "environment": settings.environment, "debug": settings.debug},
    )

    # Initialize Redis connection
    redis_client = get_redis_client()
    try:
        await redis_client.connect()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Continuing without Redis...")

    # Allow tests to skip touching the real DB (e.g., when using SQLite in-memory)
    import os

    if os.getenv("NOTEMESH_SKIP_LIFESPAN_DB") == "1":
        logger.info("Skipping DB table creation due to NOTEMESH_SKIP_LIFESPAN_DB=1")
    else:
        try:
            await create_tables()
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error("Failed to create database tables", exc_info=e)
            raise

    yield

    # Shutdown
    logger.info("Shutting down NoteMesh application")
    try:
        await redis_client.disconnect()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.warning(f"Redis disconnect failed: {e}")


app = FastAPI(
    title="NoteMesh",
    description="Note sharing and management API",
    version="0.1.0",
    lifespan=lifespan,
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(notes_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(sharing_router, prefix="/api")
app.include_router(health_router, prefix="/api")


# Root endpoint
@app.get("/")
async def root():
    return {"message": "NoteMesh API"}


# API root endpoint for better navigation
@app.get("/api/")
async def api_root():
    return {
        "message": "NoteMesh API",
        "version": "0.1.0",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "endpoints": {
            "authentication": "/api/auth/",
            "notes": "/api/notes/",
            "search": "/api/search/",
            "sharing": "/api/sharing/",
            "health": "/api/health/"
        }
    }


# Basic unprefixed health endpoint for compatibility with tests
@app.get("/health")
async def basic_health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("notemesh.main:app", host="0.0.0.0", port=8000, reload=True)
