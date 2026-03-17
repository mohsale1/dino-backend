from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from src.core.Security import get_current_user_token, decode_token
from src.config.Settings import settings
from src.repositories.UserRepository import UserRepository
from src.repositories.RoleRepository import RoleRepository

async def get_current_user(token: str = Depends(get_current_user_token)) -> Dict[str, Any]:
    """Get current user from token (works for both system and application users)"""
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user_id = payload.get("sub")
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

    if not user.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    role = role_repo.get_by_id(user.get('role_id', ''))
    if role:
        user['role'] = role

    user['user_type'] = user_type

    return user

async def get_current_system_user(token: str = Depends(get_current_user_token)) -> Dict[str, Any]:
    """Get current system user from token (or bypass if JWT disabled)"""
    # If JWT is disabled, get the default SuperAdmin user from database
    if not settings.ENABLE_JWT:
        user_repo = UserRepository("system_users")
        role_repo = RoleRepository()

        # Get first SuperAdmin user from database
        users = user_repo.get_all(filters={"email": settings.SUPERADMIN_EMAIL}, limit=1)
        if users:
            user = users[0]
            role = role_repo.get_by_id(user.get('role_id', ''))
            if role:
                user['role'] = role
            return user

        # If no SuperAdmin exists, raise error
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
    user_type = payload.get("user_type")

    if user_type != "system":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user type for this endpoint"
        )

    user_repo = UserRepository("system_users")
    role_repo = RoleRepository()

    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    role = role_repo.get_by_id(user.get('role_id', ''))
    if role:
        user['role'] = role

    return user

async def get_current_application_user(token: str = Depends(get_current_user_token)) -> Dict[str, Any]:
    """Get current application user from token (or bypass if JWT disabled)"""
    # If JWT is disabled, get the default SuperAdmin user from the application_users collection
    if not settings.ENABLE_JWT:
        user_repo = UserRepository("application_users")
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
            detail="No default application user found in database. Please run initialization."
        )

    # Normal JWT flow
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user_id = payload.get("sub")
    user_type = payload.get("user_type")

    if user_type != "application":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user type for this endpoint"
        )

    user_repo = UserRepository("application_users")
    role_repo = RoleRepository()

    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    role = role_repo.get_by_id(user.get('role_id', ''))
    if role:
        user['role'] = role

    return user
