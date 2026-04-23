import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from src.config.Database import async_session_factory, close_db, initialize_db
from src.config.Settings import settings

from src.application.routes import (
    Areas,
    Auth,
    Categories,
    Customers,
    Dashboard,
    HomePage,
    Items,
    Orders,
    Permissions,
    Personas,
    Reviews,
    Roles,
    Tables,
    Users,
    Workspaces,
)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("Starting dino-application service...")
    logger.info(f"Build ID   : {settings.BUILD_ID}")
    logger.info(f"Deployed At: {settings.DEPLOYED_AT}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    try:
        settings._validate_production_config()
        logger.info("Configuration validated.")
    except RuntimeError as e:
        logger.critical(f"Invalid production configuration:\n{e}")
        raise

    try:
        await initialize_db()
    except Exception as e:
        logger.critical(f"PostgreSQL connection failed: {e}")
        raise
    logger.info("PostgreSQL connection pool initialized.")

    yield

    logger.info("Shutting down dino-application service...")
    await close_db()
    logger.info("PostgreSQL connection pool closed.")


_docs_url = None if settings.ENVIRONMENT == "production" else "/docs"
_redoc_url = None if settings.ENVIRONMENT == "production" else "/redoc"

app = FastAPI(
    title=f"{settings.APP_NAME} - Application Service",
    version=settings.APP_VERSION,
    description="Dino Application Service API",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all application routers
PREFIX = "/api/v1/application"

app.include_router(Auth.router, prefix=PREFIX)
app.include_router(Users.router, prefix=PREFIX)
app.include_router(Personas.router, prefix=PREFIX)
app.include_router(Areas.router, prefix=PREFIX)
app.include_router(Tables.router, prefix=PREFIX)
app.include_router(Categories.router, prefix=PREFIX)
app.include_router(Items.router, prefix=PREFIX)
app.include_router(Orders.router, prefix=PREFIX)
app.include_router(Customers.router, prefix=PREFIX)
app.include_router(Workspaces.router, prefix=PREFIX)
app.include_router(Dashboard.router, prefix=PREFIX)
app.include_router(Roles.router, prefix=PREFIX)
app.include_router(Permissions.router, prefix=PREFIX)
app.include_router(Reviews.router, prefix=PREFIX)
app.include_router(HomePage.router, prefix=PREFIX)


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
    """Root endpoint."""
    response: dict = {
        "success": True,
        "message": f"Welcome to {settings.APP_NAME} Application Service",
        "version": settings.APP_VERSION,
    }
    if settings.ENVIRONMENT != "production":
        response["docs"] = "/docs"
        response["redoc"] = "/redoc"
    return response


@app.get("/health")
async def health():
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
