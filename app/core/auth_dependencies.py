"""
Authentication dependencies with conditional JWT support
Supports both JWT authentication and development mode (GCP auth)
"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.security import (
    get_current_user, 
    get_current_admin_user, 
    get_current_superadmin_user,
    get_development_user,
    get_optional_current_user
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Security scheme - conditional based on JWT_AUTH setting
security = HTTPBearer(auto_error=False)  # Don't auto-error to handle both modes


async def get_conditional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Get current user with conditional authentication:
    - If JWT_AUTH=True: Require JWT token
    - If JWT_AUTH=False: Use development user (for GCP auth environments)
    """
    try:
        # Development mode - JWT auth disabled
        if not settings.is_jwt_auth_enabled:
            logger.info("JWT authentication disabled - using development user")
            return await get_development_user()
        
        # Production mode - JWT auth required
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Use standard JWT authentication
        return await get_current_user(credentials)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Conditional authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_conditional_admin_user(
    current_user: Dict[str, Any] = Depends(get_conditional_current_user)
) -> Dict[str, Any]:
    """Get current user with admin privileges (conditional auth)"""
    user_role = current_user.get('role', 'operator')
    
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


async def get_conditional_superadmin_user(
    current_user: Dict[str, Any] = Depends(get_conditional_current_user)
) -> Dict[str, Any]:
    """Get current user with superadmin privileges (conditional auth)"""
    user_role = current_user.get('role', 'operator')
    
    if user_role != 'superadmin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin privileges required"
        )
    
    return current_user


async def get_optional_conditional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current user optionally (for public endpoints)
    Returns None if no valid authentication, doesn't raise errors
    """
    try:
        # Development mode - always return development user
        if not settings.is_jwt_auth_enabled:
            return await get_development_user()
        
        # Production mode - try to get user from JWT
        if not credentials:
            return None
        
        return await get_optional_current_user(request)
        
    except Exception as e:
        logger.debug(f"Optional conditional auth failed: {e}")
        return None


def get_auth_status() -> Dict[str, Any]:
    """Get current authentication configuration status (sanitized for security)"""
    status = {
        "jwt_auth_enabled": settings.is_jwt_auth_enabled,
        "environment": settings.ENVIRONMENT,
        "auth_mode": "JWT" if settings.is_jwt_auth_enabled else "Development/GCP"
    }
    
    # Only expose development details in non-production environments
    if not settings.is_production and not settings.is_jwt_auth_enabled:
        status.update({
            "dev_mode_active": True,
            "dev_user_role": settings.DEV_USER_ROLE
        })
    
    return status


# Convenience aliases for backward compatibility
CurrentUser = get_conditional_current_user
CurrentAdminUser = get_conditional_admin_user
CurrentSuperAdminUser = get_conditional_superadmin_user
OptionalCurrentUser = get_optional_conditional_user