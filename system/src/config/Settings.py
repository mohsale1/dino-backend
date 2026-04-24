import logging
import warnings
from typing import List
from urllib.parse import urlparse

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_DEFAULT_SECRET_KEY = "dev-secret-key-change-in-production-use-openssl-rand-hex-32"
_DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/dino_application"


class Settings(BaseSettings):
    APP_NAME: str = "DINO"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    HOST: str = "0.0.0.0"
    PORT: int = 8080

    # Deployment identity — injected at build time via Docker --build-arg or Cloud Run env vars
    # BUILD_ID   : git SHA, image tag, or CI pipeline run ID
    # DEPLOYED_AT: ISO timestamp set at build time (e.g. 2026-03-19T10:00:00Z)
    BUILD_ID: str = "local"
    DEPLOYED_AT: str = "unknown"

    # JWT Settings - SECRET_KEY should be set in production
    ENABLE_JWT: bool = True
    SECRET_KEY: str = _DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # PostgreSQL connection URL (asyncpg driver)
    DATABASE_URL: str = _DEFAULT_DATABASE_URL

    # SuperAdmin User Settings - Auto-created on first startup
    # Default credentials (can be overridden via environment variables)
    SUPERADMIN_EMAIL: str = "admin@dino.in"
    SUPERADMIN_PASSWORD: str = "Admin@dino123"
    # Create default SuperAdmin on startup (set to false to disable)
    CREATE_DEFAULT_SUPERADMIN: bool = True

    CORS_ORIGINS: str = "*"  # Default to allow all, should be restricted in production

    # Frontend URL used for QR code generation
    FRONTEND_URL: str = "http://localhost:3000"

    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        parsed = urlparse(self.DATABASE_URL)
        db_host = f"{parsed.hostname}:{parsed.port}"

        # Log configuration on startup
        logger.info("Configuration loaded:")
        logger.info(f"   Environment: {self.ENVIRONMENT}")
        logger.info(f"   Debug: {self.DEBUG}")
        logger.info(f"   Port: {self.PORT}")
        logger.info(f"   Database Host: {db_host}")
        logger.info(f"   CORS Origins: {self.CORS_ORIGINS}")
        logger.info(f"   Create Default SuperAdmin: {self.CREATE_DEFAULT_SUPERADMIN}")
        logger.info(f"   JWT Enabled: {self.ENABLE_JWT}")

        # Warn if using default values in production
        if self.ENVIRONMENT == "production" and self.SECRET_KEY == _DEFAULT_SECRET_KEY:
            warnings.warn(
                "WARNING: Using default SECRET_KEY in production! "
                "Please set a secure SECRET_KEY in environment variables.",
                UserWarning,
            )

        if self.ENVIRONMENT == "production" and "localhost" in self.DATABASE_URL:
            warnings.warn(
                "WARNING: DATABASE_URL points to localhost in production! "
                "Please set DATABASE_URL to a remote PostgreSQL instance.",
                UserWarning,
            )

        # Log SuperAdmin auto-creation status
        if self.CREATE_DEFAULT_SUPERADMIN:
            logger.info("   SuperAdmin Auto-Creation: Enabled")

    def _validate_production_config(self) -> None:
        """Raise RuntimeError for unsafe configurations in production."""
        if self.ENVIRONMENT != "production":
            return

        errors = []

        if not self.ENABLE_JWT:
            errors.append(
                "ENABLE_JWT must not be False in production. "
                "JWT authentication is required for a production deployment."
            )

        if self.SECRET_KEY == _DEFAULT_SECRET_KEY:
            errors.append(
                "SECRET_KEY is set to the default development value. "
                "Generate a secure key with: openssl rand -hex 32"
            )

        if errors:
            msg = "Production configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            raise RuntimeError(msg)


settings = Settings()
