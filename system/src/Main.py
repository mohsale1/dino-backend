import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.config.Database import async_session_factory, close_db, initialize_db
from src.config.Settings import settings
from src.core.Initializer import initialize_application

from src.system.routes import Auth as SystemAuth
from src.system.routes import Billing as SystemBilling
from src.system.routes import Dashboard as SystemDashboard
from src.system.routes import Permissions as SystemPermissions
from src.system.routes import Roles as SystemRoles
from src.system.routes import Settings as SystemSettings
from src.system.routes import Users as SystemUsers
from src.system.routes import Workspaces as SystemWorkspaces
from src.system.routes import Personas as SystemPersonas

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


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

    # Validate production config — runs after port is bound so errors appear in logs
    try:
        settings._validate_production_config()
        logger.info("[OK] Configuration validated")
    except RuntimeError as e:
        logger.critical(f"[FAIL] Invalid production configuration:\n{e}")
        raise

    # Initialize PostgreSQL connection pool — abort startup on failure
    try:
        await initialize_db()
        logger.info("[OK] PostgreSQL connection pool initialized")
    except Exception as e:
        logger.critical(f"[FAIL] PostgreSQL connection failed: {e}")
        raise

    # Initialize application resources (SuperAdmin role, etc.)
    try:
        async with async_session_factory() as db:
            await initialize_application(db)
        logger.info("[OK] Application resources initialized")
    except Exception as e:
        logger.error(f"[FAIL] Application resource initialization failed: {e}")
        logger.warning("Application will continue despite initialization errors.")

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


# Hide API docs in production
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


app.include_router(SystemAuth.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemDashboard.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemRoles.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemPermissions.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemUsers.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemWorkspaces.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemBilling.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemSettings.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemPersonas.router, prefix="/api/v1/system", tags=["System"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.Main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
