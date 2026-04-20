from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from src.core.Security import get_current_user_token, decode_token
from src.config.Settings import settings
from src.repositories.UserRepository import UserRepository
from src.repositories.RoleRepository import RoleRepository

async def get_current_user(token: str = Depends(get_current_user_token)) -> Dict[str, Any]:
    """Get current user from token (works for both system and application users)"""
    if not settings.ENABLE_JWT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject"
        )

    user_type = payload.get("user_type", "application")

    # Determine collection based on user type
    collection = "system_users" if user_type == "system" else "application_users"

    user_repo = UserRepository(collection)
    role_repo = RoleRepository()

    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    role = role_repo.get_by_id(user.get('role_id', ''))
    if role:
        user['role'] = role

    user['user_type'] = user_type

    return user

async def get_current_system_user(token: str = Depends(get_current_user_token)) -> Dict[str, Any]:
    """Get current system user from token (or bypass if JWT disabled in non-production)"""
    if not settings.ENABLE_JWT:
        if settings.ENVIRONMENT == 'production':
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="JWT must be enabled in production"
            )

        # Dev-only bypass: resolve the default SuperAdmin from the database
        user_repo = UserRepository("system_users")
        role_repo = RoleRepository()

        users = user_repo.get_all(filters={"email": settings.SUPERADMIN_EMAIL}, limit=1)
        if users:
            user = users[0]
            role = role_repo.get_by_id(user.get('role_id', ''))
            if role:
                user['role'] = role
            return user

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No SuperAdmin user found in database. Please run initialization."
        )

    # Normal JWT flow
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject"
        )

    user_type = payload.get("user_type")
    if user_type != "system":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System access required"
        )

    user_repo = UserRepository("system_users")
    role_repo = RoleRepository()

    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    role = role_repo.get_by_id(user.get('role_id', ''))
    if role:
        user['role'] = role

    return user

async def get_current_application_user(token: str = Depends(get_current_user_token)) -> Dict[str, Any]:
    """Get current application user from token"""
    if not settings.ENABLE_JWT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    # Normal JWT flow
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject"
        )

    user_repo = UserRepository("application_users")
    role_repo = RoleRepository()

    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    role = role_repo.get_by_id(user.get('role_id', ''))
    if role:
        user['role'] = role

    return user