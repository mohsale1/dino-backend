import logging
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from src.config.Settings import settings
from src.config.Database import initialize_db, close_db
from src.core.Exceptions import AppException
from src.application.middleware.SecurityHeaders import SecurityHeadersMiddleware
from src.application.exceptions import Handlers
from src.application.routes import (
    Areas, Auth, Billing, Categories, Customers, Dashboard,
    HomePage, Items, Orders, Permissions, Personas,
    PublicMenu, Reviews, Roles, Tables, Users, Workspaces,
)

logger = logging.getLogger("dino-app")

limiter = Limiter(key_func=lambda request: request.client.host)

async def lifespan(app: FastAPI):
    await initialize_db()
    yield
    await close_db()

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

# Middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SecurityHeadersMiddleware)

# Exception Handlers
app.add_exception_handler(Exception, Handlers.global_exception_handler)
app.add_exception_handler(SQLAlchemyError, Handlers.db_exception_handler)
app.add_exception_handler(RequestValidationError, Handlers.validation_exception_handler)
app.add_exception_handler(AppException, Handlers.app_exception_handler)

# Routers
PREFIX = "/api/v1/application"
for router in [
    Auth.router, Users.router, Personas.router, Areas.router, Tables.router,
    Categories.router, Items.router, Orders.router, Customers.router,
    Workspaces.router, Billing.router, Dashboard.router, Roles.router,
    Permissions.router, Reviews.router, HomePage.router, PublicMenu.router,
]:
    app.include_router(router, prefix=PREFIX)