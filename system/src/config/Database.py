"""
PostgreSQL async database configuration using SQLAlchemy 2.x + asyncpg.
"""

import logging
from typing import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.Settings import settings

logger = logging.getLogger(__name__)

engine = None
async_session_factory = None


async def initialize_db() -> None:
    """Create the async engine and session factory."""
    global engine, async_session_factory

    parsed = urlparse(settings.DATABASE_URL)
    logger.info("Connecting to PostgreSQL...")
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

    logger.info("PostgreSQL engine initialised successfully.")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a managed AsyncSession."""
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


async def close_db() -> None:
    """Dispose the engine and release all pooled connections."""
    global engine, async_session_factory

    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None
        logger.info("PostgreSQL engine disposed.")
