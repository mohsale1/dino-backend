"""
Dino E-Menu Backend API
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

# =============================================================================
# LOGGING SETUP
# =============================================================================
from app.core.logging import setup_enhanced_logging, get_logger

# Determine log level from environment
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
enable_debug = os.environ.get("DEBUG", "false").lower() == "true"

# Setup enhanced logging
setup_enhanced_logging(log_level=log_level, enable_debug=enable_debug)
logger = get_logger(__name__)

# =============================================================================
# SETTINGS
# =============================================================================
try:
    from app.core.config import settings
    logger.info("✅ Settings loaded successfully")
except Exception as e:
    logger.warning(f"⚠️ Settings loading failed: {e}")

    class MinimalSettings:
        ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")
        DEBUG = False
        LOG_LEVEL = "INFO"
        GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "unknown")
        DATABASE_NAME = os.environ.get("DATABASE_NAME", "unknown")
        is_production = True
        CORS_ORIGINS = ["*"]
        CORS_ALLOW_CREDENTIALS = True
        CORS_ALLOW_METHODS = ["*"]
        CORS_ALLOW_HEADERS = ["*"]

    settings = MinimalSettings()

# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================
try:
    from app.core.dependencies import initialize_di, check_services_health
    logger.info("✅ Dependency injection initialized successfully")
    di_available = True
except Exception as e:
    logger.warning(f"⚠️ Dependency injection initialization failed: {e}")
    di_available = False

# =============================================================================
# API ROUTER
# =============================================================================
try:
    from app.api.v1.api import api_router
    logger.info("✅ API router loaded successfully")
    api_router_available = True
except Exception as e:
    logger.warning(f"⚠️ API router loading failed: {e}")
    api_router_available = False

# =============================================================================
# LIFESPAN HANDLER
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management for Cloud Run deployment"""
    # Startup
    logger.info("🦕 Starting Dino E-Menu API...")
    logger.info("✅ Dino E-Menu API startup completed successfully")

    yield

    # Shutdown
    logger.info("🦕 Shutting down Dino E-Menu API")

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================
docs_url = "/docs" if not settings.is_production else None
redoc_url = "/redoc" if not settings.is_production else None

app = FastAPI(
    title="Dino E-Menu API",
    description="A comprehensive e-menu solution for restaurants and cafes with role-based access control",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    redirect_slashes=False,  # Prevent 307 redirects
)

# =============================================================================
# MIDDLEWARE SETUP
# =============================================================================
# Security middleware
try:
    from app.core.security import (
        SecurityHeadersMiddleware,
        RateLimitMiddleware,
        RequestValidationMiddleware,
        AuthenticationRateLimitMiddleware,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(AuthenticationRateLimitMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        calls=getattr(settings, "RATE_LIMIT_PER_MINUTE", 60),
        period=60,
    )
    logger.info("✅ Security middleware enabled")
except ImportError as e:
    logger.info(f"ℹ️ Security middleware not available: {e} - Continuing without security middleware")
except Exception as e:
    logger.warning(f"⚠️ Security middleware setup failed: {e}")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "CORS_ORIGINS", ["http://localhost:3000"]),
    allow_credentials=getattr(settings, "CORS_ALLOW_CREDENTIALS", True),
    allow_methods=getattr(settings, "CORS_ALLOW_METHODS", ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]),
    allow_headers=getattr(settings, "CORS_ALLOW_HEADERS", ["*"]),
)
logger.info("✅ CORS middleware enabled")

# =============================================================================
# ROUTES
# =============================================================================
if api_router_available:
    try:
        app.include_router(api_router, prefix="/api/v1")
        logger.info("✅ API routes included successfully")
    except Exception as e:
        logger.warning(f"⚠️ Failed to include API routes: {e}")

@app.get("/")
async def root():
    """Root endpoint - minimal response for Cloud Run"""
    return {
        "service": "dino-api",
        "version": "2.0.0",
        "status": "healthy",
        "health_endpoint": "/api/v1/health/health",
    }

# =============================================================================
# ERROR HANDLERS
# =============================================================================
try:
    from app.core.errors import (
        http_exception_handler,
        validation_exception_handler,
        api_exception_handler,
        general_exception_handler,
        APIError,
    )

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(APIError, api_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("✅ Enhanced error handlers registered")
except ImportError as e:
    logger.warning(f"⚠️ Enhanced error handlers not available: {e}")

    @app.exception_handler(500)
    async def internal_server_error(request, exc):
        """Fallback internal server error handler"""
        logger.error(
            "Internal server error occurred",
            exc_info=True,
            extra={"request_url": str(request.url), "request_method": request.method},
        )
        return {
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "status_code": 500,
        }

# =============================================================================
# LOCAL DEVELOPMENT STARTUP
# =============================================================================
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting uvicorn on port {port}...")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info",
        access_log=True,
        workers=1,  # Single worker for Cloud Run
    )