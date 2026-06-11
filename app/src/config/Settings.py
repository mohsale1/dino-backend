import logging
import warnings
from functools import cached_property
from typing import List, Optional
from urllib.parse import urlparse

from pydantic import model_validator
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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 300  # 5 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1

    # PostgreSQL connection URL (asyncpg driver)
    DATABASE_URL: str = _DEFAULT_DATABASE_URL

    # Connection pool — tune per deployment size
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 600
    DB_POOL_TIMEOUT: int = 30

    # SuperAdmin auto-creation — credentials must be supplied via env vars
    SUPERADMIN_EMAIL: Optional[str] = None
    SUPERADMIN_PASSWORD: Optional[str] = None
    CREATE_DEFAULT_SUPERADMIN: bool = True

    # CORS — comma-separated list of allowed origins, or "*" for all
    CORS_ORIGINS: str = "*"

    # Frontend URL used for QR code generation
    FRONTEND_URL: str = "http://localhost:3000"

    # Google Cloud Storage
    GCS_BUCKET_NAME: str = ""
    GCS_CREDENTIALS_PATH: Optional[str] = None  # Path to service account JSON; None = ADC

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @cached_property
    def cors_origins_list(self) -> List[str]:
        """Parsed CORS origins — computed once and cached."""
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        if not self.CORS_ORIGINS.strip():
            return []
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @model_validator(mode="after")
    def _validate_and_log(self) -> "Settings":
        """Run after all fields are set — log config and emit production warnings."""
        parsed = urlparse(self.DATABASE_URL)
        db_host = f"{parsed.hostname}:{parsed.port}"

        logger.info("Configuration loaded:")
        logger.info("   Environment : %s", self.ENVIRONMENT)
        logger.info("   Debug       : %s", self.DEBUG)
        logger.info("   Port        : %s", self.PORT)
        logger.info("   DB Host     : %s", db_host)
        logger.info("   CORS        : %r", self.CORS_ORIGINS)
        logger.info("   JWT Enabled : %s", self.ENABLE_JWT)
        logger.info("   Pool Size   : %s (+%s overflow)", self.DB_POOL_SIZE, self.DB_MAX_OVERFLOW)
        logger.info("   GCS Bucket  : %s", self.GCS_BUCKET_NAME or "NOT SET")

        if self.CREATE_DEFAULT_SUPERADMIN and self.SUPERADMIN_EMAIL and self.SUPERADMIN_PASSWORD:
            logger.info("   SuperAdmin Auto-Creation: Enabled")

        if self.ENVIRONMENT == "production":
            self._production_warnings()
            self._production_errors()

        return self

    def _production_warnings(self) -> None:
        """Emit non-fatal warnings for risky production configurations."""
        if self.SECRET_KEY == _DEFAULT_SECRET_KEY:
            warnings.warn(
                "SECRET_KEY is the default dev value in production. "
                "Set a secure SECRET_KEY env var (openssl rand -hex 32).",
                UserWarning, stacklevel=2,
            )
        if "localhost" in self.DATABASE_URL:
            warnings.warn(
                "DATABASE_URL points to localhost in production. "
                "Set DATABASE_URL to a remote PostgreSQL instance.",
                UserWarning, stacklevel=2,
            )
        if self.CORS_ORIGINS.strip() == "*":
            warnings.warn(
                "CORS_ORIGINS is '*' in production. "
                "Restrict to specific trusted origins.",
                UserWarning, stacklevel=2,
            )
        if self.CREATE_DEFAULT_SUPERADMIN and not (
            self.SUPERADMIN_EMAIL and self.SUPERADMIN_PASSWORD
        ):
            warnings.warn(
                "CREATE_DEFAULT_SUPERADMIN=True but credentials not set. "
                "SuperAdmin will NOT be created. Set SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD.",
                UserWarning, stacklevel=2,
            )

    def _production_errors(self) -> None:
        """Raise RuntimeError for configurations that make the service non-functional."""
        errors = []

        if not self.ENABLE_JWT:
            errors.append(
                "ENABLE_JWT must not be False in production. "
                "JWT authentication is required."
            )

        if errors:
            raise RuntimeError(
                "Production configuration errors:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )


settings = Settings()
