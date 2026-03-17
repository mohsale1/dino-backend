from pydantic_settings import BaseSettings
from typing import List, Optional
import warnings
import os

class Settings(BaseSettings):
    APP_NAME: str = "DINO"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False 
    ENVIRONMENT: str = "production"
    
    HOST: str = "0.0.0.0"
    PORT: int = 8080 
    
    # JWT Settings - SECRET_KEY should be set in production
    ENABLE_JWT: bool = os.getenv("ENABLE_JWT", "false").lower() == "true"
    SECRET_KEY: str = "dev-secret-key-change-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Firebase Settings - Uses Application Default Credentials (ADC)
    # ADC works automatically in Cloud Run, Cloud Functions, GCE
    # For local dev: run 'gcloud auth application-default login'
    FIREBASE_PROJECT_ID: str = os.getenv("PROJECT_ID", "dev-project-id")
    FIREBASE_DATABASE_ID: str = os.getenv("DATABASE_NAME", "(default)")
    
    # SuperAdmin User Settings - Auto-created on first startup
    # Default credentials (can be overridden via environment variables)
    SUPERADMIN_EMAIL: str = os.getenv("SUPERADMIN_EMAIL", "admin@dino.in")
    SUPERADMIN_PASSWORD: str = os.getenv("SUPERADMIN_PASSWORD", "Admin@dino123")
    # Create default SuperAdmin on startup (set to false to disable)
    CREATE_DEFAULT_SUPERADMIN: bool = os.getenv("CREATE_DEFAULT_SUPERADMIN", "true").lower() == "true"
    
    CORS_ORIGINS: str = "*"  # Default to allow all, should be restricted in production
    
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
        # Don't fail if .env file doesn't exist (for Cloud Run)
        env_file_required = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Log configuration on startup
        print(f"⚙️  Configuration loaded:")
        print(f"   Environment: {self.ENVIRONMENT}")
        print(f"   Debug: {self.DEBUG}")
        print(f"   Port: {self.PORT}")
        print(f"   Firebase Project: {self.FIREBASE_PROJECT_ID}")
        print(f"   CORS Origins: {self.CORS_ORIGINS}")
        print(f"   Create Default SuperAdmin: {self.CREATE_DEFAULT_SUPERADMIN}")
        print(f"   JWT Enabled: {self.ENABLE_JWT}")
        
        # Warn if using default values in production
        if self.ENVIRONMENT == "production" and self.SECRET_KEY == "dev-secret-key-change-in-production-use-openssl-rand-hex-32":
            warnings.warn(
                "⚠️  WARNING: Using default SECRET_KEY in production! "
                "Please set a secure SECRET_KEY in environment variables.",
                UserWarning
            )
        
        if self.ENVIRONMENT == "production" and self.FIREBASE_PROJECT_ID == "dev-project-id":
            warnings.warn(
                "⚠️  WARNING: Using default FIREBASE_PROJECT_ID in production! "
                "Please set FIREBASE_PROJECT_ID in environment variables.",
                UserWarning
            )
        
        # Log SuperAdmin auto-creation status
        if self.CREATE_DEFAULT_SUPERADMIN:
            print(f"   SuperAdmin Auto-Creation: Enabled")
            print(f"   SuperAdmin Email: {self.SUPERADMIN_EMAIL}")

settings = Settings()
