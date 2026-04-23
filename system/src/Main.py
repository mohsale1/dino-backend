import logging
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

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    _banner = "=" * 60
    logger.info(_banner)
    logger.info("  DINO SYSTEM — STARTING UP")
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
        await initialize_db()
        logger.info("[OK] PostgreSQL connection pool initialized")
    except Exception as e:
        logger.critical(f"[FAIL] PostgreSQL connection failed: {e}")
        raise

    logger.info(_banner)
    logger.info(f"  DINO SYSTEM — READY  (build: {settings.BUILD_ID})")
    logger.info(_banner)

    yield

    logger.info(_banner)
    logger.info("  DINO SYSTEM — SHUTTING DOWN")
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
    description="Dino System Service — system-level administration and management",
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
    """Global exception handler"""
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
    """Root endpoint"""
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
    """Health check endpoint — probes live PostgreSQL connectivity."""
    if async_session_factory is None:
        return {"status": "starting"}
    try:
        async with async_session_factory() as db:
            await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check failed — PostgreSQL unreachable: {e}")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.Main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
