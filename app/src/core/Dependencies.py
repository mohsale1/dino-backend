"""
FastAPI dependency functions for dino-application.

Resolves the authenticated application user (user_type=1) from a JWT token.
Uses the unified users table.
"""

from decimal import Decimal
from typing import Any, Dict, List

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.Database import get_db
from src.core.Security import decode_token, get_current_user_token
from src.models.Permission import Permission
from src.models.Role import Role
from src.models.User import User


# --------------------------------------------------------------------------- #
# Internal helpers                                                             #
# --------------------------------------------------------------------------- #

_USER_SAFE_FIELDS: frozenset = frozenset([
    "id", "user_type", "email", "first_name", "last_name", "phone",
    "role_id", "workspace_id", "last_login", "is_active", "created_at", "updated_at",
])


def _coerce_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _extract_permission_codenames(permissions: List[Permission]) -> List[str]:
    """Return permission codenames as 'resource:action' strings."""
    codenames: List[str] = []
    for perm in permissions:
        resource = getattr(perm, "resource", None)
        action = getattr(perm, "action", None)
        if resource and action:
            codenames.append(f"{resource}:{action}")
    return codenames


async def _fetch_application_user(user_id: int, db: AsyncSession) -> Dict[str, Any]:
    """Query User (user_type=1) + Role + Permissions in a single round-trip."""
    stmt = (
        select(User)
        .where(
            User.id == user_id,
            User.is_active.is_(True),
            User.user_type == 1,
        )
        .options(selectinload(User.role).selectinload(Role.permissions))
    )
    result = await db.execute(stmt)
    user_obj = result.scalar_one_or_none()

    if user_obj is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user_dict: Dict[str, Any] = {
        field: _coerce_value(getattr(user_obj, field, None))
        for field in _USER_SAFE_FIELDS
        if hasattr(user_obj, field)
    }

    role_obj = user_obj.role
    if role_obj is not None:
        user_dict["role"] = {
            "id": role_obj.id,
            "name": role_obj.name,
            "role_type": role_obj.role_type,
            "permissions": _extract_permission_codenames(role_obj.permissions),
        }

    return user_dict


# --------------------------------------------------------------------------- #
# Public dependency functions                                                  #
# --------------------------------------------------------------------------- #

async def get_current_application_user(
    token: str = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Resolve the authenticated application user (user_type=1) from a JWT token."""
    payload = decode_token(token)

    user_type = payload.get("user_type")
    if user_type != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Application access required",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    try:
        uid = int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: subject is not a valid user ID",
        )

    return await _fetch_application_user(uid, db)



async def get_current_user(
    token: str = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Generic current-user dependency — same as get_current_application_user."""
    return await get_current_application_user(token=token, db=db)
