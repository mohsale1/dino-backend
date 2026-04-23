"""
FastAPI dependency functions for dino-system.

Resolves the authenticated user from a JWT token (or dev bypass).
Uses the unified users table — user_type=0 for system users.
"""

from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.Database import get_db
from src.config.Settings import settings
from src.core.Security import decode_token, get_current_user_token
from src.models.Permission import Permission
from src.models.Role import Role
from src.models.User import User


# --------------------------------------------------------------------------- #
# Internal helpers                                                             #
# --------------------------------------------------------------------------- #

def _row_to_dict(obj: Any) -> Dict[str, Any]:
    """Convert a SQLAlchemy ORM instance to a plain dict."""
    result: Dict[str, Any] = {}
    for col in obj.__table__.columns:
        value = getattr(obj, col.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = float(value)
        result[col.name] = value
    return result


def _extract_permission_codenames(permissions: List[Permission]) -> List[str]:
    """Return permission codenames as 'resource:action' strings.

    Format: "{resource}:{action}"
    Examples: "users:read", "billing:update", "workspaces:delete"

    This matches the codename format expected by BaseRoleCheck.check_permission
    and all SystemPermissionCheck.require() calls in the route layer.
    """
    codenames: List[str] = []
    for perm in permissions:
        resource = getattr(perm, "resource", None)
        action = getattr(perm, "action", None)
        if resource and action:
            codenames.append(f"{resource}:{action}")
    return codenames



async def _fetch_user_by_id(
    user_id: int,
    db: AsyncSession,
    require_system: bool = True,
) -> Dict[str, Any]:
    """Query User + Role (with permissions) by primary key."""
    stmt = (
        select(User)
        .where(User.id == user_id, User.is_active.is_(True))
        .options(selectinload(User.role).selectinload(Role.permissions))
    )
    if require_system:
        stmt = stmt.where(User.user_type == 0)

    result = await db.execute(stmt)
    user_obj = result.scalar_one_or_none()

    if user_obj is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or access denied",
        )

    return _build_user_dict(user_obj)


async def _fetch_user_by_email(
    email: str,
    db: AsyncSession,
    require_system: bool = True,
) -> Dict[str, Any]:
    """Query User + Role (with permissions) by email (dev bypass only)."""
    stmt = (
        select(User)
        .where(User.email == email, User.is_active.is_(True))
        .options(selectinload(User.role).selectinload(Role.permissions))
    )
    if require_system:
        stmt = stmt.where(User.user_type == 0)

    result = await db.execute(stmt)
    user_obj = result.scalar_one_or_none()

    if user_obj is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No SuperAdmin user found in database. Please run initialization.",
        )

    return _build_user_dict(user_obj)


def _build_user_dict(user_obj: User) -> Dict[str, Any]:
    """Serialise a User ORM object, strip password_hash, and attach role with permissions."""
    user_dict = _row_to_dict(user_obj)
    user_dict.pop("password_hash", None)

    role_obj = user_obj.role
    if role_obj is not None:
        role_dict = _row_to_dict(role_obj)
        role_dict["permissions"] = _extract_permission_codenames(role_obj.permissions)
        user_dict["role"] = role_dict

    return user_dict


# --------------------------------------------------------------------------- #
# Public dependency functions                                                  #
# --------------------------------------------------------------------------- #

async def get_current_system_user(
    token: str = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Resolve the authenticated system user (user_type=0) from a JWT token.

    Dev bypass
    ----------
    When ``settings.ENABLE_JWT`` is False (non-production only) the token is
    ignored and the SuperAdmin account is returned directly from the database.
    """
    if not settings.ENABLE_JWT:
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="JWT must be enabled in production",
            )
        return await _fetch_user_by_email(settings.SUPERADMIN_EMAIL, db, require_system=True)

    payload = decode_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    user_type = payload.get("user_type")
    if user_type != 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System access required",
        )

    return await _fetch_user_by_id(int(user_id), db, require_system=True)


async def get_current_user(
    token: str = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Generic current-user dependency — accepts both user_type 0 and 1.

    Dev bypass follows the same rules as ``get_current_system_user``.
    """
    if not settings.ENABLE_JWT:
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="JWT must be enabled in production",
            )
        return await _fetch_user_by_email(settings.SUPERADMIN_EMAIL, db, require_system=True)

    payload = decode_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    user_type = payload.get("user_type")
    if user_type not in (0, 1):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid user access required",
        )

    require_system = user_type == 0
    return await _fetch_user_by_id(int(user_id), db, require_system=require_system)
