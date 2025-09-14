from logging.config import fileConfig
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

# ensure backend/src is on sys.path so we can import the app metadata
backend_root = Path(__file__).resolve().parents[1]  # backend directory
src_path = str(backend_root / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# load .env from backend directory if present
dotenv_path = backend_root / ".env"


def _load_dotenv_safe(path: Path) -> None:
    """Try to load .env using python-dotenv if available, otherwise fall back to a safe manual parser.
    Manual parser ignores comments, blank lines, 'export ' prefix and preserves existing env vars.
    """
    if not path.exists():
        return

    # try python-dotenv first
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(dotenv_path=str(path), override=False)
        return
    except Exception:
        # fall through to manual parsing
        pass

    try:
        with path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export ") :].lstrip()
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                # remove surrounding quotes if present
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                # set only if not already present in environment
                os.environ.setdefault(key, val)
    except Exception:
        # don't raise — alembic should continue and fail later with a clear message if vars missing
        return


# load .env safely
_load_dotenv_safe(dotenv_path)

# import the application's metadata so autogenerate can see models
try:
    # Import all models to ensure they're registered with the metadata
    from notemesh.core.models.base import BaseModel
    from notemesh.core.models.user import User
    from notemesh.core.models.note import Note
    from notemesh.core.models.tag import Tag, NoteTag
    from notemesh.core.models.share import Share
    from notemesh.core.models.refresh_token import RefreshToken

    target_metadata = BaseModel.metadata
except Exception as e:
    print(f"Warning: Could not import models: {e}")
    target_metadata = None

# helper to build a PostgreSQL URL from environment variables
def _build_postgresql_url() -> str | None:
    # prefer explicit full URL from alembic config or env vars
    cfg = context.config.get_section(context.config.config_ini_section) or {}
    url = cfg.get("sqlalchemy.url") or os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URL")
    if url:
        # Ensure it's a PostgreSQL URL
        if not url.startswith("postgresql"):
            raise ValueError(f"Only PostgreSQL is supported. Got: {url}")
        return url

    # fallback to individual env vars
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    db = os.environ.get("DB_NAME", "notemesh")
    user = os.environ.get("DB_USER", "notemesh")
    pwd = os.environ.get("DB_PASSWORD") or os.environ.get("POSTGRES_PASSWORD")
    if not pwd:
        return None

    user_enc = quote_plus(user)
    pwd_enc = quote_plus(pwd)
    return f"postgresql+asyncpg://{user_enc}:{pwd_enc}@{host}:{port}/{db}"


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a bound connection (sync)."""
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations(url: str) -> None:
    """Run migrations for an async engine."""
    connectable: AsyncEngine = create_async_engine(url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point used by alembic - PostgreSQL only."""
    cfg = context.config.get_section(context.config.config_ini_section) or {}
    url = cfg.get("sqlalchemy.url") or _build_postgresql_url()
    if not url:
        raise RuntimeError("No PostgreSQL database URL available for Alembic (set DATABASE_URL or DB_* env vars)")

    # PostgreSQL with asyncpg
    if url.startswith("postgresql+asyncpg"):
        import asyncio
        asyncio.run(run_async_migrations(url))
    # PostgreSQL with psycopg2/psycopg
    elif url.startswith("postgresql"):
        # For sync PostgreSQL drivers
        connectable = engine_from_config(
            {"sqlalchemy.url": url},
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            do_run_migrations(connection)
    else:
        raise ValueError(f"Only PostgreSQL is supported. Got URL: {url}")


# entrypoint
if context.is_offline_mode():
    # offline behavior
    cfg = context.config.get_section(context.config.config_ini_section) or {}
    url = cfg.get("sqlalchemy.url") or _build_postgresql_url()
    if not url:
        raise RuntimeError("No PostgreSQL database URL available for Alembic offline mode")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()
else:
    run_migrations_online()
