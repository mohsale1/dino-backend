import logging
import warnings
from typing import List, Optional
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict

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
    BUILD_ID: str = "local"
    DEPLOYED_AT: str = "unknown"

    # JWT — SECRET_KEY must be set in production via env var
    ENABLE_JWT: bool = True
    SECRET_KEY: str = _DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # PostgreSQL connection URL (asyncpg driver)
    DATABASE_URL: str = _DEFAULT_DATABASE_URL

    # SuperAdmin auto-creation — credentials must be supplied via env vars
    SUPERADMIN_EMAIL: Optional[str] = None
    SUPERADMIN_PASSWORD: Optional[str] = None
    CREATE_DEFAULT_SUPERADMIN: bool = True

    # CORS — comma-separated list of allowed origins, or "*" for all
    CORS_ORIGINS: str = "*"

    # Frontend URL used for QR code generation
    FRONTEND_URL: str = "http://localhost:3000"

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        if not self.CORS_ORIGINS.strip():
            return []
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        parsed = urlparse(self.DATABASE_URL)
        db_host = f"{parsed.hostname}:{parsed.port}"

        logger.info("Configuration loaded:")
        logger.info(f"   Environment: {self.ENVIRONMENT}")
        logger.info(f"   Debug: {self.DEBUG}")
        logger.info(f"   Port: {self.PORT}")
        logger.info(f"   Database Host: {db_host}")
        logger.info(f"   CORS Origins: {self.CORS_ORIGINS!r}")
        logger.info(f"   Create Default SuperAdmin: {self.CREATE_DEFAULT_SUPERADMIN}")
        logger.info(f"   JWT Enabled: {self.ENABLE_JWT}")

        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY == _DEFAULT_SECRET_KEY:
                warnings.warn(
                    "WARNING: SECRET_KEY is the default dev value in production. "
                    "Set a secure SECRET_KEY env var (openssl rand -hex 32).",
                    UserWarning,
                )
            if "localhost" in self.DATABASE_URL:
                warnings.warn(
                    "WARNING: DATABASE_URL points to localhost in production. "
                    "Set DATABASE_URL to a remote PostgreSQL instance.",
                    UserWarning,
                )
            if self.CORS_ORIGINS.strip() == "*":
                warnings.warn(
                    "WARNING: CORS_ORIGINS is '*' in production. "
                    "Restrict to specific trusted origins.",
                    UserWarning,
                )
            if self.CREATE_DEFAULT_SUPERADMIN and not (
                self.SUPERADMIN_EMAIL and self.SUPERADMIN_PASSWORD
            ):
                warnings.warn(
                    "WARNING: CREATE_DEFAULT_SUPERADMIN=True but credentials not set. "
                    "SuperAdmin will NOT be created. Set SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD.",
                    UserWarning,
                )

        if self.CREATE_DEFAULT_SUPERADMIN and self.SUPERADMIN_EMAIL and self.SUPERADMIN_PASSWORD:
            logger.info("   SuperAdmin Auto-Creation: Enabled")

        self._validate_production_config()

    def _validate_production_config(self) -> None:
        """Raise RuntimeError only for configurations that make the service non-functional."""
        if self.ENVIRONMENT != "production":
            return

        errors = []

        if not self.ENABLE_JWT:
            errors.append(
                "ENABLE_JWT must not be False in production. "
                "JWT authentication is required."
            )

        if errors:
            msg = "Production configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            raise RuntimeError(msg)


settings = Settings()
