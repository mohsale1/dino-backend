"""
PostgreSQL async database configuration using SQLAlchemy 2.x + asyncpg.

Two engines are managed:
  - engine               : primary application DB  (DATABASE_URL)
  - system_engine        : dino-system DB          (SYSTEM_DATABASE_URL)

When SYSTEM_DATABASE_URL is absent or identical to DATABASE_URL the system
engine is not created and get_system_db() yields the same session as get_db(),
avoiding an unnecessary second connection pool.
"""

import logging
from typing import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.Settings import settings

logger = logging.getLogger(__name__)

# Primary application DB
engine = None
async_session_factory = None

# dino-system DB (only allocated when a distinct URL is configured)
system_engine = None
system_session_factory = None


async def initialize_db() -> None:
    """Create the async engine(s) and session factory(ies)."""
    global engine, async_session_factory, system_engine, system_session_factory

    parsed = urlparse(settings.DATABASE_URL)
    logger.info("Connecting to PostgreSQL (application DB)...")
    logger.info(f"   Host: {parsed.hostname}:{parsed.port}")
    logger.info(f"   Database: {parsed.path.lstrip('/')}")

    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.DEBUG,
    )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("PostgreSQL application engine initialised successfully.")

    # Only create a second engine when a distinct system DB URL is configured.
    if settings.uses_separate_system_db:
        sys_parsed = urlparse(settings.SYSTEM_DATABASE_URL)
        logger.info("Connecting to PostgreSQL (system DB)...")
        logger.info(f"   Host: {sys_parsed.hostname}:{sys_parsed.port}")
        logger.info(f"   Database: {sys_parsed.path.lstrip('/')}")

        system_engine = create_async_engine(
            settings.SYSTEM_DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.DEBUG,
        )

        system_session_factory = async_sessionmaker(
            system_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info("PostgreSQL system engine initialised successfully.")
    else:
        logger.info(
            "SYSTEM_DATABASE_URL not set or identical to DATABASE_URL — "
            "reusing primary session for cross-service queries."
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a managed AsyncSession (application DB)."""
    if async_session_factory is None:
        raise RuntimeError("Database not initialised. Call initialize_db() on startup.")

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_system_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a managed AsyncSession for the system DB.

    When no separate system DB is configured this transparently yields a
    session from the primary pool so callers need not branch on configuration.
    """
    factory = system_session_factory if system_session_factory is not None else async_session_factory

    if factory is None:
        raise RuntimeError("Database not initialised. Call initialize_db() on startup.")

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Dispose all engines and release all pooled connections."""
    global engine, async_session_factory, system_engine, system_session_factory

    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None
        logger.info("PostgreSQL application engine disposed.")

    if system_engine is not None:
        await system_engine.dispose()
        system_engine = None
        system_session_factory = None
        logger.info("PostgreSQL system engine disposed.")
