"""
Alembic Environment Configuration - dino-system
Async migration runner using SQLAlchemy asyncpg engine.
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Ensure the project root (containing src/) is importable regardless of
# where alembic CLI is invoked from (container /app or local checkout).
# ---------------------------------------------------------------------------
_here = os.path.dirname(os.path.abspath(__file__))          # .../src/alembic
_project_root = os.path.abspath(os.path.join(_here, "..", ".."))  # project root
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ---------------------------------------------------------------------------
# Import Base and all model modules so that Base.metadata is fully populated
# before Alembic inspects it for autogenerate / target_metadata.
# ---------------------------------------------------------------------------
from src.models.Base import Base  # noqa: F401
import src.models.Permission        # noqa: F401
import src.models.Role              # noqa: F401
import src.models.User              # noqa: F401
import src.models.Workspace         # noqa: F401
import src.models.WorkspaceBilling    # noqa: F401
import src.models.BillingTransaction  # noqa: F401
import src.models.Persona             # noqa: F401

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Normalize DATABASE_URL and set it on the config
# _normalize_db_url returns (clean_url, connect_args) — we only need the
# clean URL here; connect_args are applied in run_async_migrations.
# ---------------------------------------------------------------------------
_raw_url = os.environ.get("DATABASE_URL")
if not _raw_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set."
    )

from src.config.Database import _normalize_db_url
_clean_url, _connect_args = _normalize_db_url(_raw_url)
config.set_main_option("sqlalchemy.url", _clean_url)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration mode
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
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
    Run migrations using asyncpg. SSL is passed via connect_args —
    never as a query string parameter.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=_connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()