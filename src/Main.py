from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from src.config.Settings import settings
from src.config.Database import initialize_firestore, close_firestore
from src.core.Initializer import initialize_application

from src.system.routes import Auth as SystemAuth
from src.system.routes import Dashboard as SystemDashboard
from src.system.routes import Workspaces as SystemWorkspaces
from src.system.routes import Billing as SystemBilling
from src.system.routes import Registration as SystemRegistration
from src.system.routes import Roles as SystemRoles
from src.system.routes import Permissions as SystemPermissions
from src.system.routes import Users as SystemUsers
from src.system.routes import Settings as SystemSettings

from src.application.routes import Auth as ApplicationAuth
from src.application.routes import Orders as ApplicationOrders
from src.application.routes import Organizations as ApplicationOrganizations
from src.application.routes import Menu as ApplicationMenu
from src.application.routes import Areas as ApplicationAreas
from src.application.routes import Categories as ApplicationCategories
from src.application.routes import Items as ApplicationItems
from src.application.routes import Tables as ApplicationTables
from src.application.routes import Coupons as ApplicationCoupons
from src.application.routes import HomePage as ApplicationHomePage
from src.application.routes import Dashboard as ApplicationDashboard
from src.application.routes import Reviews as ApplicationReviews
from src.application.routes import Users as ApplicationUsers

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting application...")
    
    # Initialize Firestore
    try:
        initialize_firestore()
        logger.info("✓ Firestore initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {e}")
        logger.warning("Application will start without Firestore connection")
    
    # Initialize application resources (SuperAdmin role, etc.)
    try:
        await initialize_application()
        logger.info("✓ Application resources initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application resources: {e}")
        logger.warning("Application will continue despite initialization errors")
    
    yield
    
    logger.info("Shutting down application...")
    try:
        close_firestore()
    except Exception as e:
        logger.error(f"Error closing Firestore: {e}")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A modular two-tier order management system with role-based access control",
    lifespan=lifespan
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
            "error": str(exc) if settings.DEBUG else "An error occurred"
        }
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "success": True,
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "success": True,
        "status": "healthy",
        "version": settings.APP_VERSION
    }

app.include_router(SystemAuth.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemDashboard.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemRoles.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemPermissions.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemUsers.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemWorkspaces.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemBilling.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemRegistration.router, prefix="/api/v1/system", tags=["System"])
app.include_router(SystemSettings.router, prefix="/api/v1/system", tags=["System"])

app.include_router(ApplicationAuth.router, prefix="/api/v1/application", tags=["Application"])
app.include_router(ApplicationUsers.router, prefix="/api/v1/application", tags=["Application"])
app.include_router(ApplicationOrders.router, prefix="/api/v1/application", tags=["Application"])
app.include_router(ApplicationOrganizations.router, prefix="/api/v1/application", tags=["Application"])
app.include_router(ApplicationMenu.router, prefix="/api/v1/application", tags=["Application"])
app.include_router(ApplicationAreas.router, prefix="/api/v1/application", tags=["Application"])
app.include_router(ApplicationCategories.router, prefix="/api/v1/application", tags=["Application"])
app.include_router(ApplicationItems.router, prefix="/api/v1/application", tags=["Application"])
app.include_router(ApplicationTables.router, prefix="/api/v1/application", tags=["Application"])
app.include_router(ApplicationCoupons.router, prefix="/api/v1/application", tags=["Application"])
app.include_router(ApplicationDashboard.router, prefix="/api/v1/application", tags=["Application"])
app.include_router(ApplicationReviews.router, prefix="/api/v1/application", tags=["Application"])

app.include_router(ApplicationHomePage.router, prefix="/api/v1/application", tags=["Application"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.Main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
