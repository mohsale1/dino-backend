import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

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

def _get_real_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_get_real_ip)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("Starting dino-application service...")
    logger.info(f"Build ID   : {settings.BUILD_ID}")
    logger.info(f"Deployed At: {settings.DEPLOYED_AT}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    logger.info("Configuration validated.")

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
# When CORS_ORIGINS is "*" we cannot use allow_origins=["*"] together with
# allow_credentials=True — browsers reject that combination.  Instead we use
# allow_origin_regex=".*" which makes Starlette reflect the actual request
# Origin back, satisfying the browser while still permitting every origin.
_cors_origins = settings.cors_origins_list
if _cors_origins == ["*"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

# TrustedHostMiddleware — reads ALLOWED_HOSTS from the environment.
# MUST be configured in production: set the ALLOWED_HOSTS env var to a
# comma-separated list of permitted hostnames (e.g. "api.example.com,www.example.com").
# Leaving it unset defaults to "*" (no restriction), which is insecure in production.
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=os.environ.get("ALLOWED_HOSTS", "*").split(","),
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


@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=503,
        content={"success": False, "message": "Service temporarily unavailable", "error": "Database error"},
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
            "error": "An error occurred",
        },
    )


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-XSS-Protection"] = "0"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


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
                "detail": "PostgreSQL connectivity check failed",
            },
        )
    return {
        "success": True,
        "status": "healthy",
    }
