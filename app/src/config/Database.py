"""
PostgreSQL async database configuration using SQLAlchemy 2.x + asyncpg.
"""

import logging
from typing import AsyncGenerator
from urllib.parse import urlparse  # used for hostname/port logging only

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.Settings import settings

logger = logging.getLogger(__name__)

engine = None
async_session_factory = None


def _normalize_db_url(url: str) -> tuple:
    """
    Normalize a PostgreSQL connection URL for SQLAlchemy 2.x + asyncpg.

    Returns (clean_url, connect_args) where:
      - clean_url   : postgresql+asyncpg://... with NO query string
      - connect_args: dict to pass to create_async_engine(connect_args=...)
                      contains {"ssl": ssl.SSLContext} when SSL is required

    asyncpg does not accept sslmode/ssl as query string parameters —
    SSL must be passed via connect_args.

    NOTE: urlparse does not correctly parse non-standard schemes such as
    postgresql+asyncpg://, so we use plain string operations to strip the
    query string reliably.
    """
    import ssl as _ssl

    # 1. Normalise scheme — covers all common variants incl. already-correct ones
    for prefix in (
        "postgresql+psycopg2://",
        "postgresql+asyncpg://",
        "postgresql://",
        "postgres://",
    ):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix):]
            break

    # 2. Split on '?' using plain string ops — urlparse misparses non-standard schemes
    if "?" in url:
        clean_url, qs = url.split("?", 1)
    else:
        clean_url, qs = url, ""

    # 3. Parse query string into a dict
    params: dict = {}
    for part in qs.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            params[k.lower()] = v.lower()

    # 4. Build connect_args for SSL
    connect_args: dict = {}
    sslmode = params.get("sslmode", params.get("ssl", ""))
    if sslmode and sslmode not in ("disable", "allow", "prefer", "false", "0", ""):
        # require / verify-ca / verify-full / true → enable SSL
        connect_args["ssl"] = _ssl.create_default_context()

    return clean_url, connect_args




async def initialize_db() -> None:
    """Create the async engine and session factory."""
    global engine, async_session_factory

    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None

    db_url, connect_args = _normalize_db_url(settings.DATABASE_URL)
    parsed = urlparse(db_url)
    logger.info("Connecting to PostgreSQL (application DB)...")
    logger.info(f"   Host: {parsed.hostname}:{parsed.port}")
    logger.info(f"   Database: {parsed.path.lstrip('/')}")

    engine = create_async_engine(
        db_url,
        connect_args=connect_args,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=600,
        pool_timeout=30,
        echo=settings.DEBUG and settings.ENVIRONMENT != "production",
    )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("PostgreSQL application engine initialised successfully.")


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
        logger.info("PostgreSQL application engine disposed.")
