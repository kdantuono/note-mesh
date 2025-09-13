from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio

from alembic import context

# Import our models for autogenerate support
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from notemesh.core.models import BaseModel
from notemesh.config import settings
from dotenv import load_dotenv

# Load project .env (adjust path if your layout differs)
project_root = os.path.join(os.path.dirname(__file__), "..", "..")
load_dotenv(os.path.join(project_root, ".env"))

# prefer env var, fallback to alembic.ini value
db_url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")

# If app uses async driver for runtime, convert to sync URL for Alembic autogenerate:
# postgresql+asyncpg:// -> postgresql://
if db_url and "+asyncpg" in db_url:
    sync_db_url = db_url.replace("+asyncpg", "")
else:
    sync_db_url = db_url

if sync_db_url:
    config.set_main_option("sqlalchemy.url", sync_db_url)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override the sqlalchemy.url from config if environment variable exists
if settings.database_url:
    config.set_main_option('sqlalchemy.url', settings.database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = BaseModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    def do_run_migrations(connection):
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    async def run_async_migrations():
        """Create async engine and run migrations."""
        connectable = create_async_engine(
            config.get_main_option("sqlalchemy.url"),
            future=True,
        )

        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

        await connectable.dispose()

    # Run async migrations
    asyncio.run(run_async_migrations())


# Force offline mode for initial migration creation
if context.is_offline_mode() or True:  # Always use offline for now
    run_migrations_offline()
else:
    run_migrations_online()
