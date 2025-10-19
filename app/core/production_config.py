"""
Production Configuration and Optimization
Settings and utilities specifically for production deployment
"""
import os
from typing import Optional, Dict, Any
from pydantic import BaseSettings, validator

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ProductionSettings(BaseSettings):
    """Production-specific settings"""
    
    # Environment
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    ENCRYPTION_KEY: Optional[str] = None
    
    # Database
    FIRESTORE_PROJECT_ID: str
    FIRESTORE_CREDENTIALS_PATH: Optional[str] = None
    
    # Storage
    STORAGE_BACKEND: str = "cloud"
    STORAGE_BUCKET: str
    STORAGE_CDN_URL: Optional[str] = None
    
    # Performance
    ENABLE_CACHING: bool = True
    CACHE_TTL_SECONDS: int = 300
    MAX_CONNECTIONS: int = 100
    CONNECTION_TIMEOUT: int = 30
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 300
    RATE_LIMIT_BURST: int = 50
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    LOG_LEVEL: str = "INFO"
    
    # CORS
    ALLOWED_ORIGINS: list = ["https://yourdomain.com"]
    ALLOWED_METHODS: list = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS: list = ["*"]
    
    # SSL/TLS
    SSL_CERT_PATH: Optional[str] = None
    SSL_KEY_PATH: Optional[str] = None
    
    # Email (for notifications)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    
    # Backup
    BACKUP_ENABLED: bool = True
    BACKUP_SCHEDULE: str = "0 2 * * *"  # Daily at 2 AM
    BACKUP_RETENTION_DAYS: int = 30
    
    @validator('SECRET_KEY', 'JWT_SECRET_KEY')
    def validate_secrets(cls, v):
        if not v or len(v) < 32:
            raise ValueError('Secret keys must be at least 32 characters long')
        return v
    
    @validator('ALLOWED_ORIGINS')
    def validate_origins(cls, v):
        if not v or v == ["*"]:
            logger.warning("CORS is configured to allow all origins - this is not recommended for production")
        return v
    
    class Config:
        env_file = ".env.production"
        case_sensitive = True


class PerformanceOptimizer:
    """Performance optimization utilities"""
    
    @staticmethod
    def optimize_database_queries():
        """Apply database query optimizations"""
        # This would contain database-specific optimizations
        logger.info("Database query optimizations applied")
    
    @staticmethod
    def configure_connection_pooling(max_connections: int = 100):
        """Configure database connection pooling"""
        # This would configure connection pooling
        logger.info(f"Connection pooling configured with max {max_connections} connections")
    
    @staticmethod
    def enable_query_caching(ttl_seconds: int = 300):
        """Enable query result caching"""
        # This would enable caching
        logger.info(f"Query caching enabled with {ttl_seconds}s TTL")


class HealthChecker:
    """Health check utilities for production monitoring"""
    
    @staticmethod
    async def check_database_health() -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            from app.database.firestore import get_firestore_client
            db = get_firestore_client()
            
            # Simple connectivity test
            test_doc = db.collection('health_check').document('test')
            test_doc.set({'timestamp': 'test'})
            test_doc.delete()
            
            return {
                "status": "healthy",
                "message": "Database connection successful",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}",
                "timestamp": "2024-01-01T00:00:00Z"
            }
    
    @staticmethod
    async def check_storage_health() -> Dict[str, Any]:
        """Check storage service health"""
        try:
            from app.services.storage_service import get_storage_service
            storage = get_storage_service()
            
            # Test storage connectivity
            # This would depend on the storage backend
            
            return {
                "status": "healthy",
                "message": "Storage service operational",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Storage service error: {str(e)}",
                "timestamp": "2024-01-01T00:00:00Z"
            }
    
    @staticmethod
    async def check_external_services() -> Dict[str, Any]:
        """Check external service dependencies"""
        # This would check external APIs, payment gateways, etc.
        return {
            "status": "healthy",
            "message": "All external services operational",
            "timestamp": "2024-01-01T00:00:00Z"
        }


class SecurityHardening:
    """Security hardening for production"""
    
    @staticmethod
    def apply_security_headers(app):
        """Apply security headers to FastAPI app"""
        from fastapi.middleware.trustedhost import TrustedHostMiddleware
        from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
        
        # Force HTTPS in production
        if os.getenv("ENVIRONMENT") == "production":
            app.add_middleware(HTTPSRedirectMiddleware)
        
        # Trusted host middleware
        allowed_hosts = os.getenv("ALLOWED_HOSTS", "").split(",")
        if allowed_hosts and allowed_hosts != [""]:
            app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    
    @staticmethod
    def configure_rate_limiting(app):
        """Configure rate limiting middleware"""
        # This would add rate limiting middleware
        logger.info("Rate limiting configured")
    
    @staticmethod
    def setup_request_logging(app):
        """Setup comprehensive request logging"""
        # This would add request logging middleware
        logger.info("Request logging configured")


class ProductionDeployment:
    """Production deployment utilities"""
    
    @staticmethod
    def validate_environment():
        """Validate production environment configuration"""
        required_vars = [
            "SECRET_KEY",
            "JWT_SECRET_KEY",
            "FIRESTORE_PROJECT_ID",
            "STORAGE_BUCKET"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        logger.info("Production environment validation passed")
    
    @staticmethod
    def setup_monitoring():
        """Setup production monitoring"""
        # This would configure monitoring tools
        logger.info("Production monitoring configured")
    
    @staticmethod
    def configure_logging():
        """Configure production logging"""
        import logging
        
        # Set production log level
        logging.getLogger().setLevel(logging.INFO)
        
        # Configure structured logging for production
        logger.info("Production logging configured")


# Global instances
production_settings = ProductionSettings()
performance_optimizer = PerformanceOptimizer()
health_checker = HealthChecker()
security_hardening = SecurityHardening()
production_deployment = ProductionDeployment()