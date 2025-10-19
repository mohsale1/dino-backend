"""
Simplified Dependency Injection Container
Streamlined service management with essential services only
"""
from typing import Dict, Any, Optional, Callable
from functools import lru_cache

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ServiceContainer:
    """Simplified service container for essential services"""
    
    def __init__(self):
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        
    def register_singleton(self, name: str, factory: Callable) -> None:
        """Register a singleton service"""
        self._factories[name] = factory
        logger.debug(f"Registered singleton: {name}")
    
    def get_service(self, name: str) -> Any:
        """Get service instance"""
        if name not in self._factories:
            raise ValueError(f"Service {name} not registered")
        
        if name not in self._singletons:
            self._singletons[name] = self._factories[name]()
            logger.debug(f"Created singleton instance: {name}")
        
        return self._singletons[name]
    
    def get_all_services(self) -> Dict[str, str]:
        """Get list of all registered services"""
        return {
            "registered": list(self._factories.keys()),
            "instantiated": list(self._singletons.keys())
        }


# Global service container
container = ServiceContainer()


def register_core_services():
    """Register essential application services"""
    
    # Repository Manager
    def create_repository_manager():
        from app.database.repository_manager import RepositoryManager
        return RepositoryManager()
    
    container.register_singleton("repository_manager", create_repository_manager)
    
    # Auth Service
    def create_auth_service():
        from app.services.auth_service import AuthService
        return AuthService()
    
    container.register_singleton("auth_service", create_auth_service)
    
    # Validation Service
    def create_validation_service():
        from app.services.validation_service import ValidationService
        return ValidationService()
    
    container.register_singleton("validation_service", create_validation_service)
    
    # Role Permission Service
    def create_role_permission_service():
        from app.services.role_permission_service import RolePermissionService
        return RolePermissionService()
    
    container.register_singleton("role_permission_service", create_role_permission_service)
    
    logger.info("Core services registered successfully")


# Service accessor functions
@lru_cache(maxsize=1)
def get_repository_manager():
    """Get repository manager instance"""
    return container.get_service("repository_manager")


@lru_cache(maxsize=1)
def get_auth_service():
    """Get auth service instance"""
    return container.get_service("auth_service")


@lru_cache(maxsize=1)
def get_validation_service():
    """Get validation service instance"""
    return container.get_service("validation_service")


@lru_cache(maxsize=1)
def get_role_permission_service():
    """Get role permission service instance"""
    return container.get_service("role_permission_service")


def get_container() -> ServiceContainer:
    """Get service container"""
    return container


def initialize_di():
    """Initialize dependency injection container"""
    try:
        register_core_services()
        logger.info("Dependency injection initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DI container: {e}")
        raise


def check_services_health() -> Dict[str, Any]:
    """Check health of all registered services"""
    health_status = {
        "container_status": "healthy",
        "services": container.get_all_services()
    }
    
    try:
        # Test key services
        services_to_test = [
            ("repository_manager", get_repository_manager),
            ("auth_service", get_auth_service),
            ("validation_service", get_validation_service),
            ("role_permission_service", get_role_permission_service)
        ]
        
        for service_name, service_getter in services_to_test:
            try:
                service_getter()
                health_status[service_name] = "healthy"
            except Exception as e:
                health_status[service_name] = f"error: {str(e)}"
                
    except Exception as e:
        health_status["container_status"] = f"error: {str(e)}"
    
    return health_status


# Auto-initialize when module is imported
initialize_di()