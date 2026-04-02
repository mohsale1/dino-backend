import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.Settings import settings
from src.config.Database import initialize_firestore, close_firestore

from src.application.routes import (
    Auth,
    Orders,
    Organizations,
    Menu,
    Areas,
    Categories,
    Items,
    Tables,
    Coupons,
    HomePage,
    Dashboard,
    Reviews,
    Users,
    Permissions,
    Roles,
)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("Starting dino-application service...")
    logger.info(f"Build ID   : {settings.BUILD_ID}")
    logger.info(f"Deployed At: {settings.DEPLOYED_AT}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize Firestore connection
    initialize_firestore()
    logger.info("Firestore initialized.")

    yield

    # Shutdown
    logger.info("Shutting down dino-application service...")
    close_firestore()
    logger.info("Firestore connection closed.")


app = FastAPI(
    title=f"{settings.APP_NAME} - Application Service",
    version=settings.APP_VERSION,
    description="Dino Application Service API",
    lifespan=lifespan,
)

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
app.include_router(Orders.router, prefix=PREFIX)
app.include_router(Organizations.router, prefix=PREFIX)
app.include_router(Menu.router, prefix=PREFIX)
app.include_router(Areas.router, prefix=PREFIX)
app.include_router(Categories.router, prefix=PREFIX)
app.include_router(Items.router, prefix=PREFIX)
app.include_router(Tables.router, prefix=PREFIX)
app.include_router(Coupons.router, prefix=PREFIX)
app.include_router(HomePage.router, prefix=PREFIX)
app.include_router(Dashboard.router, prefix=PREFIX)
app.include_router(Reviews.router, prefix=PREFIX)
app.include_router(Users.router, prefix=PREFIX)
app.include_router(Permissions.router, prefix=PREFIX)
app.include_router(Roles.router, prefix=PREFIX)


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
    """Health check endpoint — probes live Firestore connectivity."""
    from src.config.Database import get_firestore_client
    try:
        db = get_firestore_client()
        db.collection("_health").limit(1).get()
    except Exception as e:
        logger.error(f"Health check failed — Firestore unreachable: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "status": "unhealthy",
                "version": settings.APP_VERSION,
                "detail": "Firestore connectivity check failed",
            },
        )
    return {
        "success": True,
        "status": "healthy",
        "version": settings.APP_VERSION,
    }