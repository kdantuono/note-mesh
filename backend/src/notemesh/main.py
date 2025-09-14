# Main application entry point
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_tables
from .api import auth_router, notes_router, search_router, sharing_router, health_router
from .config import get_settings
from .core.logging import setup_logging, LoggingMiddleware, get_logger

# Setup logging first
setup_logging()
logger = get_logger("main")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting NoteMesh application", extra={
        'version': '0.1.0',
        'environment': settings.environment,
        'debug': settings.debug
    })

    try:
        await create_tables()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error("Failed to create database tables", exc_info=e)
        raise

    yield

    # Shutdown
    logger.info("Shutting down NoteMesh application")


app = FastAPI(
    title="NoteMesh",
    description="Note sharing and management API",
    version="0.1.0",
    lifespan=lifespan
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


# Basic unprefixed health endpoint for compatibility with tests
@app.get("/health")
async def basic_health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "notemesh.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )