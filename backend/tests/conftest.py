"""
Shared pytest fixtures for all tests.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from src.notemesh.main import app
from src.notemesh.database import get_db_session
from src.notemesh.core.models.base import BaseModel
from src.notemesh.config import Settings, get_settings
from src.notemesh.security.password import hash_password
from src.notemesh.security.jwt import create_access_token


# Test database URL - using SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_DATABASE_URL_SYNC = "sqlite:///:memory:"


# --- Test-local SQLite shims for Postgres-specific types (UUID, ARRAY) ---
# This avoids changing production code while allowing model tests to run on SQLite.
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy import String
import json

try:
    # Render PostgreSQL UUID as CHAR(36) on SQLite
    @compiles(PGUUID, "sqlite")
    def _compile_uuid_sqlite(type_, compiler, **kw):
        return "CHAR(36)"
except Exception:
    # If compiles was already registered in another test run, ignore
    pass


@pytest.fixture(scope="session", autouse=True)
def sqlite_type_shims():
    """Monkeypatch custom types to be SQLite-friendly for tests.

    - Map HttpUrlListType (ARRAY on PG) to a JSON string stored in a VARCHAR on SQLite.
    - UUID mapping is handled by the @compiles decorator above.
    """
    # Only apply when using SQLite in tests
    if not TEST_DATABASE_URL.startswith("sqlite"):
        yield
        return

    # Lazy import to avoid affecting production modules
    from src.notemesh.core.models.types import HttpUrlListType

    # Keep original methods to restore if needed (not necessary across session scope)
    def _load_dialect_impl(self, dialect):
        # On SQLite, fallback to String storage (JSON-encoded)
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String(2000))
        # Default path (Postgres ARRAY)
        return dialect.type_descriptor(self.impl)

    def _process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            # Store as JSON string
            urls = [str(u) for u in value]
            # Enforce max 500 chars per URL similar to PG constraint by raising
            for u in urls:
                if len(u) > 500:
                    raise ValueError("Hyperlink exceeds maximum length of 500 characters")
            return json.dumps(urls)
        # On PG, store as list of strings
        return [str(u) for u in value]

    def _process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            # Parse JSON string back to list of strings
            try:
                return json.loads(value)
            except Exception:
                return value
        # On PG, it's already a list of strings
        return value

    # Apply monkeypatches
    HttpUrlListType.load_dialect_impl = _load_dialect_impl  # type: ignore[attr-defined]
    HttpUrlListType.process_bind_param = _process_bind_param  # type: ignore[assignment]
    HttpUrlListType.process_result_value = _process_result_value  # type: ignore[assignment]

    yield


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        secret_key="test-secret-key",
        debug=True,
        redis_url="redis://localhost:6379/15",  # Use different Redis DB for tests
    )


@pytest.fixture(scope="function")
async def test_engine(test_settings):
    """Create a fresh test database engine per test for isolation."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        # Use a single in-memory connection shared across the async engine
        poolclass=StaticPool,
        echo=False,
    )

    # Create tables
    async with engine.begin() as conn:
        # Ensure all model modules are imported so tables are registered
        # before calling create_all on the metadata. Without these imports,
        # the metadata may be empty and tables won't be created.
        from src.notemesh.core.models import (
            user as _m_user,
            note as _m_note,
            tag as _m_tag,
            share as _m_share,
            refresh_token as _m_refresh_token,
        )
        await conn.run_sync(BaseModel.metadata.create_all)

    try:
        yield engine
    finally:
        # Clean up
        await engine.dispose()


class EagerAsyncSession(AsyncSession):
    """AsyncSession that eagerly refreshes relationship attributes by default.

    This helps avoid MissingGreenlet errors in tests by pre-loading relationships
    during refresh() so later attribute access doesn't trigger implicit IO.
    """

    async def refresh(self, instance, attribute_names=None, with_for_update=None, identity_token=None):
        # If caller didn't specify which attributes to refresh, include relationships too
        if attribute_names is None:
            try:
                rel_names = list(instance.__mapper__.relationships.keys())
            except Exception:
                rel_names = []
            # Refresh scalar state first
                await super().refresh(instance, attribute_names=None, with_for_update=with_for_update)
            # Then refresh relationships explicitly within the async context
            for rel_name in rel_names:
                try:
                        await super().refresh(instance, attribute_names=[rel_name], with_for_update=with_for_update)
                except Exception:
                    # Ignore if relationship can't be refreshed (e.g., not persisted yet)
                    pass
        else:
                await super().refresh(instance, attribute_names=attribute_names, with_for_update=with_for_update)


@pytest.fixture
async def test_session(test_engine):
    """Create a test database session."""
    async_session_maker = sessionmaker(
        test_engine,
        class_=EagerAsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture
def override_get_db(test_session):
    """Override the get_db dependency."""
    async def _override_get_db():
        yield test_session
    
    return _override_get_db


@pytest.fixture
def test_app(override_get_db, test_settings):
    """Create test FastAPI app with overridden dependencies."""
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
async def async_client(test_app):
    """Create async test client."""
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "username": f"testuser_{uuid4().hex[:8]}",
        "password": "TestPassword123!",
        "full_name": "Test User",
    }


@pytest.fixture
async def test_user(test_session, test_user_data):
    """Create a test user in the database."""
    from src.notemesh.core.models.user import User
    
    user = User(
        username=test_user_data["username"],
        password_hash=hash_password(test_user_data["password"]),
        full_name=test_user_data["full_name"],
        is_active=True,
        is_verified=True,
    )
    
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    
    # Add the plain password to the user object for testing
    user.plain_password = test_user_data["password"]
    
    return user


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers with a valid JWT token."""
    token_data = {"sub": str(test_user.id)}
    access_token = create_access_token(token_data)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def test_note_data():
    """Sample note data for testing."""
    return {
        "title": "Test Note",
        "content": "This is a test note content",
        "is_pinned": False,
        "tags": ["test", "example"],
    }


@pytest.fixture
async def test_note(test_session, test_user, test_note_data):
    """Create a test note in the database."""
    from src.notemesh.core.models.note import Note
    from src.notemesh.core.models.tag import Tag
    
    note = Note(
        title=test_note_data["title"],
        content=test_note_data["content"],
        is_pinned=test_note_data["is_pinned"],
        user_id=test_user.id,
    )
    
    # Add tags
    for tag_name in test_note_data["tags"]:
        tag = Tag(name=tag_name)
        note.tags.append(tag)
    
    test_session.add(note)
    await test_session.commit()
    await test_session.refresh(note)
    
    return note


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis for testing."""
    class MockRedis:
        def __init__(self):
            self.storage = {}
        
        async def get(self, key):
            return self.storage.get(key)
        
        async def set(self, key, value, ex=None):
            self.storage[key] = value
        
        async def delete(self, key):
            if key in self.storage:
                del self.storage[key]
        
        async def exists(self, key):
            return key in self.storage
    
    mock_redis_instance = MockRedis()
    
    # You might need to patch the actual Redis client creation
    # This depends on how Redis is integrated in your app
    return mock_redis_instance