import logging
import os
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from src.config.Database import async_session_factory, close_db, initialize_db
from src.config.Settings import settings
from src.core.Exceptions import AppException

from src.application.routes import (
    Areas,
    Auth,
    Billing,
    Categories,
    Customers,
    Dashboard,
    HomePage,
    Items,
    Orders,
    Permissions,
    Personas,
    PublicMenu,
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


# ---------------------------------------------------------------------------
# Security headers middleware
#
# Implemented as a raw ASGI middleware class rather than @app.middleware("http")
# or BaseHTTPMiddleware.
#
# Why not @app.middleware("http") / BaseHTTPMiddleware?
#   Both wrap call_next() which routes the request through an anyio memory
#   stream, adding async overhead on every single request — even health checks.
#
# Raw ASGI middleware calls the next app directly with (scope, receive, send)
# and intercepts the "http.response.start" message to inject headers before
# the first byte is sent to the client. Zero buffering, zero extra tasks.
#
# Static headers are stored as a pre-built list of byte-pairs at class level
# so they are computed exactly once at import time, not on every request.
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware:
    """
    Injects security headers into every HTTP response.

    Headers injected on every response:
      - X-Content-Type-Options: nosniff
      - X-Frame-Options: DENY
      - Referrer-Policy: no-referrer
      - X-XSS-Protection: 0

    Header injected only on HTTPS responses:
      - Strict-Transport-Security: max-age=63072000; includeSubDomains

    HTTPS detection checks both the raw scheme and X-Forwarded-Proto so the
    HSTS header is set correctly when the app runs behind a TLS-terminating
    load balancer (GCP, AWS ALB, nginx, etc.) that forwards requests as plain
    HTTP internally.
    """

    # Pre-built as raw bytes — computed once at class definition, never again.
    _STATIC_HEADERS: list[tuple[bytes, bytes]] = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options",        b"DENY"),
        (b"referrer-policy",        b"no-referrer"),
        (b"x-xss-protection",       b"0"),
    ]
    _HSTS_HEADER: tuple[bytes, bytes] = (
        b"strict-transport-security",
        b"max-age=63072000; includeSubDomains",
    )

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            # Pass websocket / lifespan scopes straight through untouched.
            await self.app(scope, receive, send)
            return

        # Determine once per request whether HTTPS is in use.
        headers_map = dict(scope.get("headers", []))
        forwarded_proto = headers_map.get(b"x-forwarded-proto", b"").decode()
        is_https = scope.get("scheme") == "https" or forwarded_proto == "https"

        extra_headers = list(self._STATIC_HEADERS)
        if is_https:
            extra_headers.append(self._HSTS_HEADER)

        async def send_with_security_headers(message) -> None:
            if message["type"] == "http.response.start":
                # Append our headers to whatever the route already set.
                message["headers"] = list(message.get("headers", [])) + extra_headers
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("Starting dino-application service...")
    logger.info(f"Build ID   : {settings.BUILD_ID}")
    logger.info(f"Deployed At: {settings.DEPLOYED_AT}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

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

# Security headers — registered first so it is the outermost wrapper.
# Starlette processes add_middleware() calls in LIFO order, so the last
# middleware added runs first. SecurityHeadersMiddleware must be outermost
# (runs last on the way out) so it can inject headers after all other
# middleware and route handlers have finished.
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware
# When CORS_ORIGINS is "*" we cannot use allow_origins=["*"] together with
# allow_credentials=True — browsers reject that combination. Instead we use
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
# comma-separated list of permitted hostnames (e.g. "api.example.com").
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
app.include_router(Billing.router, prefix=PREFIX)
app.include_router(Dashboard.router, prefix=PREFIX)
app.include_router(Roles.router, prefix=PREFIX)
app.include_router(Permissions.router, prefix=PREFIX)
app.include_router(Reviews.router, prefix=PREFIX)
app.include_router(HomePage.router, prefix=PREFIX)
app.include_router(PublicMenu.router, prefix=PREFIX)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle all typed application exceptions with a consistent error envelope."""
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic / FastAPI request validation errors — return structured field errors."""
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(p) for p in err.get("loc", []) if p != "body")
        errors.append({"field": loc or "request", "message": err.get("msg", "Invalid value")})
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "errors": errors,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(
        "Database error on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=503,
        content={
            "success": False,
            "error_code": "DATABASE_ERROR",
            "message": "Service temporarily unavailable",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
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
                "error_code": "DATABASE_ERROR",
                "status": "unhealthy",
                "message": "PostgreSQL connectivity check failed",
            },
        )
    return {"success": True, "status": "healthy"}