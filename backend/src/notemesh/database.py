# Database connection setup
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from .core.models.base import BaseModel

# Database URL from env
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/notemesh")

# Create async engine
ECHO_SQL = os.getenv("ECHO_SQL", "False").lower() in ("true", "1", "yes")
engine = create_async_engine(DATABASE_URL, echo=ECHO_SQL)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db_session():
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)