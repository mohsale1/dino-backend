"""
Alembic Environment Configuration - dino-system
Async migration runner using SQLAlchemy asyncpg engine.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Import Base and all model modules so that Base.metadata is fully populated
# before Alembic inspects it for autogenerate / target_metadata.
# ---------------------------------------------------------------------------
from src.models.Base import Base  # noqa: F401 - registers DeclarativeBase

# Import every model module so their Table objects are attached to Base.metadata.
# Association tables (role_permissions, workspace_personas) are defined
# inside Role.py and Workspace.py respectively and are pulled in automatically.
import src.models.Permission        # noqa: F401
import src.models.Role              # noqa: F401
import src.models.User              # noqa: F401
import src.models.Workspace         # noqa: F401
import src.models.WorkspaceBilling    # noqa: F401
import src.models.BillingTransaction  # noqa: F401
import src.models.Persona             # noqa: F401

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with the DATABASE_URL environment variable.
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Expected format: postgresql+asyncpg://user:password@host:5432/dbname"
    )
config.set_main_option("sqlalchemy.url", database_url)

# Target metadata for autogenerate support
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration mode
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration mode (async)
# ---------------------------------------------------------------------------

def do_run_migrations(connection: Connection) -> None:
    """Execute migrations against the provided synchronous connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Create an async engine and run migrations inside a synchronous
    connection context (required by Alembic's connection-based API).
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using the async engine."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
