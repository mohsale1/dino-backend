import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.config.Database import async_session_factory, close_db, initialize_db
from src.config.Settings import settings
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.system.routes import Auth as SystemAuth
from src.system.routes import Billing as SystemBilling
from src.system.routes import Dashboard as SystemDashboard
from src.system.routes import Permissions as SystemPermissions
from src.system.routes import Personas as SystemPersonas
from src.system.routes import Roles as SystemRoles
from src.system.routes import Users as SystemUsers
from src.system.routes import Workspaces as SystemWorkspaces
from src.system.routes import WorkspaceRequests as SystemWorkspaceRequests

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


async def _run_migrations() -> None:
    """
    Run Alembic migrations fully in-process using the Python API.

    Strategy:
      1. Connect via asyncpg to check the current alembic_version.
      2. Load the ScriptDirectory to find the head revision.
      3. If already at head, skip.
      4. Otherwise run upgrade using EnvironmentContext.configure() on a
         live synchronous connection â€” no subprocess, no env.py file
         loading, no double-connection conflicts.
         EnvironmentContext.__enter__ installs the 'op' proxy that
         migration scripts depend on (from alembic import op).

    SSL is passed via connect_args; the URL never carries ?sslmode=...
    """
    import asyncpg
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.runtime.environment import EnvironmentContext
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import pool as sa_pool
    from src.config.Database import _normalize_db_url

    raw_url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
    clean_url, connect_args = _normalize_db_url(raw_url)

    # asyncpg uses the plain postgresql:// scheme
    dsn = clean_url.replace("postgresql+asyncpg://", "postgresql://")
    ssl_ctx = connect_args.get("ssl")

    # ------------------------------------------------------------------
    # Step 1 â€” check current revision via asyncpg
    # ------------------------------------------------------------------
    current_revision = None
    try:
        conn = await asyncpg.connect(dsn=dsn, ssl=ssl_ctx)
        try:
            exists = await conn.fetchval(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables"
                "  WHERE table_name = 'alembic_version'"
                ")"
            )
            if exists:
                current_revision = await conn.fetchval(
                    "SELECT version_num FROM alembic_version LIMIT 1"
                )
        finally:
            await conn.close()
    except Exception as exc:
        logger.warning(
            f"Could not check alembic_version: {exc} â€” will attempt migration anyway."
        )

    # ------------------------------------------------------------------
    # Step 2 â€” resolve head revision from the script directory
    # ------------------------------------------------------------------
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "src/alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", clean_url)

    script = ScriptDirectory.from_config(alembic_cfg)
    head_revision = script.get_current_head()

    if current_revision is None:
        logger.info("Fresh database â€” running full migration from base...")
    elif current_revision == head_revision:
        logger.info(
            f"Database already at head ({head_revision}) â€” no migrations needed."
        )
        return
    else:
        logger.info(
            f"Database at {current_revision}, head is {head_revision} â€” upgrading..."
        )

    # ------------------------------------------------------------------
    # Step 3 â€” run upgrade in-process via EnvironmentContext
    #
    # EnvironmentContext.__enter__ installs the 'op' proxy (and the
    # 'context' proxy) that migration scripts import at module level.
    # We call env_ctx.configure(connection=sync_conn) to bind the live
    # connection, then env_ctx.run_migrations() to execute the steps.
    # env.py is never loaded â€” we replicate exactly what it does.
    # ------------------------------------------------------------------
    def _do_upgrade(sync_conn):
        with EnvironmentContext(
            alembic_cfg,
            script,
            fn=lambda rev, context: script._upgrade_revs("head", rev),
            as_sql=False,
            starting_rev=None,
            destination_rev="head",
        ) as env_ctx:
            env_ctx.configure(
                connection=sync_conn,
                target_metadata=None,
                compare_type=True,
                transaction_per_migration=True,
            )
            env_ctx.run_migrations()

    async_engine = create_async_engine(
        clean_url,
        connect_args=connect_args,
        poolclass=sa_pool.NullPool,
    )
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(_do_upgrade)
    finally:
        await async_engine.dispose()

    logger.info("Alembic upgrade head completed successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    _banner = "=" * 60
    logger.info(_banner)
    logger.info("  DINO SYSTEM â€” STARTING UP")
    logger.info(_banner)
    logger.info(f"  App Version  : {settings.APP_VERSION}")
    logger.info(f"  Build ID     : {settings.BUILD_ID}")
    logger.info(f"  Deployed At  : {settings.DEPLOYED_AT}")
    logger.info(f"  Environment  : {settings.ENVIRONMENT}")
    logger.info(f"  Port         : {settings.PORT}")
    logger.info(f"  Database     : PostgreSQL (asyncpg)")
    logger.info(_banner)

    try:
        settings._validate_production_config()
        logger.info("[OK] Configuration validated")
    except RuntimeError as e:
        logger.critical(f"[FAIL] Invalid production configuration:\n{e}")
        raise

    try:
        await _run_migrations()
        logger.info("[OK] Database migrations applied")
    except Exception as e:
        logger.critical(f"[FAIL] Migration failed: {e}", exc_info=True)
        raise

    try:
        await initialize_db()
        logger.info("[OK] PostgreSQL connection pool initialized")
    except Exception as e:
        logger.critical(f"[FAIL] PostgreSQL connection failed: {e}")
        raise

    logger.info(_banner)
    logger.info(f"  DINO SYSTEM â€” READY  (build: {settings.BUILD_ID})")
    logger.info(_banner)

    yield

    logger.info(_banner)
    logger.info("  DINO SYSTEM â€” SHUTTING DOWN")
    logger.info(_banner)
    try:
        await close_db()
        logger.info("[OK] PostgreSQL connection pool closed")
    except Exception as e:
        logger.error(f"[FAIL] Error closing database connection: {e}")


_docs_url = None if settings.ENVIRONMENT == "production" else "/docs"
_redoc_url = None if settings.ENVIRONMENT == "production" else "/redoc"

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Dino System Service system-level administration and management",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred",
        },
    )


@app.get("/")
async def root():
    """Root endpoint."""
    response: dict = {
        "success": True,
        "message": f"Welcome to {settings.APP_NAME} System Service",
        "version": settings.APP_VERSION,
    }
    if settings.ENVIRONMENT != "production":
        response["docs"] = "/docs"
        response["redoc"] = "/redoc"
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint â€” probes live PostgreSQL connectivity."""
    if async_session_factory is None:
        return {"status": "starting"}
    try:
        async with async_session_factory() as db:
            await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check failed â€” PostgreSQL unreachable: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "status": "unhealthy",
                "version": settings.APP_VERSION,
                "detail": "PostgreSQL connectivity check failed",
            },
        )
    return {
        "success": True,
        "status": "healthy",
        "version": settings.APP_VERSION,
    }


_PREFIX = "/api/v1/system"

app.include_router(SystemAuth.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemDashboard.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemRoles.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemPermissions.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemUsers.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemWorkspaces.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemBilling.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemPersonas.router, prefix=_PREFIX, tags=["System"])
app.include_router(SystemWorkspaceRequests.router, prefix=_PREFIX, tags=["System"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.Main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )