"""Shared pytest fixtures configured to use SQLite in-memory for unit tests."""

import asyncio
import logging
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import attributes as orm_attributes
from sqlalchemy.orm import selectinload, sessionmaker
from sqlalchemy.pool import StaticPool

from src.notemesh.config import Settings, get_settings
from src.notemesh.core.models.base import BaseModel
from src.notemesh.database import get_db_session
from src.notemesh.main import app
from src.notemesh.security.jwt import create_access_token
from src.notemesh.security.password import hash_password

# Silence extremely verbose DEBUG logs from aiosqlite to keep test output readable
logging.getLogger("aiosqlite").setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing using SQLite in-memory DB."""
    db_url = "sqlite+aiosqlite:///:memory:"
    # Tell app lifespan to skip real DB init
    os.environ["NOTEMESH_SKIP_LIFESPAN_DB"] = "1"
    return Settings(
        database_url=db_url,
        secret_key="test-secret-key",
        debug=True,
        redis_url=os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15"),
    )


@pytest.fixture(scope="session")
async def test_engine(test_settings):
    """Create a shared SQLite in-memory engine for the test session."""
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        poolclass=StaticPool,  # keep the same memory DB across connections
        connect_args={"check_same_thread": False},
    )

    # Ensure SQLite enforces foreign key constraints (required for CASCADE/SET NULL)
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    # Create tables once per session (we'll drop/create per test session fixture)
    async with engine.begin() as conn:
        from src.notemesh.core.models import note as _m_note
        from src.notemesh.core.models import refresh_token as _m_refresh_token
        from src.notemesh.core.models import share as _m_share
        from src.notemesh.core.models import tag as _m_tag
        from src.notemesh.core.models import user as _m_user

        await conn.run_sync(BaseModel.metadata.create_all)

    try:
        yield engine
    finally:
        await engine.dispose()


class EagerAsyncSession(AsyncSession):
    """AsyncSession that eagerly refreshes relationship attributes by default.

    This helps avoid MissingGreenlet errors in tests by pre-loading relationships
    during refresh() so later attribute access doesn't trigger implicit IO.
    """

    async def get(
        self,
        entity,
        ident,
        *,
        options=None,
        populate_existing: bool = False,  # noqa: ARG002 - kept for signature compatibility
        with_for_update=None,  # noqa: ARG002 - not used here
        identity_token=None,  # noqa: ARG002 - not used here
        execution_options=None,
    ):
        """Fetch by primary key via explicit SELECT to avoid identity-map refreshes.

        Rationale: After DB-level cascades (e.g., ON DELETE CASCADE), the identity map
        may still contain an expired instance. The default .get() could try to refresh
        that instance and trigger unexpected IO paths leading to MissingGreenlet in
        async tests. We bypass that by always issuing a direct SELECT and returning
        the first row (or None).
        """
        stmt = select(entity).where(getattr(entity, "id") == ident)
        # Always populate existing identity map objects with fresh DB values
        # so that DB-level cascades (e.g., SET NULL) are visible immediately.
        stmt = stmt.execution_options(populate_existing=True)
        if options:
            stmt = stmt.options(*options)
        result = await self.execute(stmt, execution_options=execution_options or {})
        return result.scalars().first()

    async def refresh(self, instance, attribute_names=None, with_for_update=None):
        """Refresh the given instance, then proactively refresh relationships.

        - First refresh scalar/column state (or requested attributes) using the
          normal AsyncSession.refresh.
        - If no explicit attribute_names were provided, iterate the mapped
          relationships and refresh each one explicitly so that subsequent
          attribute access doesn't attempt an implicit (lazy) load.
        """
        # Always refresh the base state first
        await super().refresh(
            instance,
            attribute_names=attribute_names,
            with_for_update=with_for_update,
        )

        # If caller didn't request specific attributes, also proactively load
        # ALL relationship attributes via a dedicated SELECT with selectinload
        # so that later attribute access doesn't attempt implicit async IO.
        # Use a simple re-entrancy guard to avoid nested calls when refresh()
        # itself was invoked by a higher-level loader (e.g. inside get()).
        if attribute_names is None and not getattr(self, "_in_preload_refresh", False):
            try:
                self._in_preload_refresh = True
                mapper = instance.__mapper__
                rels = list(mapper.relationships)
                if not rels:
                    return

                # Build loader options to eager-load each relationship
                loaders = [selectinload(getattr(instance.__class__, rel.key)) for rel in rels]

                # Figure out primary key identity; assume single-column PK (BaseModel.id)
                identity = getattr(instance, "id", None)
                if identity is None:
                    return

                # Load a fresh copy with relationships populated using an explicit SELECT
                stmt = (
                    select(instance.__class__)
                    .options(*loaders)
                    .where(getattr(instance.__class__, "id") == identity)
                )
                result = await self.execute(stmt)
                loaded = result.scalars().first()
                if not loaded:
                    return

                # Copy loaded relationship values into the original instance state
                for rel in rels:
                    try:
                        value = getattr(loaded, rel.key)
                        orm_attributes.set_committed_value(instance, rel.key, value)
                    except Exception:
                        # Best effort; continue on any individual relationship failure
                        continue
            except Exception:
                # If any unexpected error occurs, fall back silently
                return
            finally:
                self._in_preload_refresh = False


@pytest.fixture
async def test_session(test_engine):
    """Create a clean test database session per test (drop/create all)."""
    async_session_maker = sessionmaker(
        test_engine,
        class_=EagerAsyncSession,
        # Avoid implicit attribute refreshes after commit which can cause
        # MissingGreenlet when accessed in sync contexts during async tests.
        expire_on_commit=False,
    )

    # Ensure a clean schema for each test to avoid unique collisions
    async with test_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
        await conn.run_sync(BaseModel.metadata.create_all)

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
        owner_id=test_user.id,
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
