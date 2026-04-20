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
from src.models.SystemUser import SystemUser


# --------------------------------------------------------------------------- #
# Internal helpers                                                             #
# --------------------------------------------------------------------------- #

def _row_to_dict(obj: Any) -> Dict[str, Any]:
    """Convert a SQLAlchemy ORM instance to a plain dict.

    Type coercions applied:
      - datetime -> ISO-8601 str
      - Decimal  -> float
      - everything else passes through unchanged
    """
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
    """Return the list of permission codenames from an eagerly loaded list of
    Permission ORM objects.

    Uses the ``name`` column on the Permission model as the codename
    (e.g. ``"workspace:read"``, ``"billing:manage"``).
    """
    codenames: List[str] = []
    for perm in permissions:
        codename = getattr(perm, "name", None)
        if codename:
            codenames.append(codename)
    return codenames


async def _fetch_system_user_by_id(user_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Query SystemUser + Role (with permissions) by primary key in one query.

    Raises HTTP 401 if the user does not exist or is inactive.
    """
    stmt = (
        select(SystemUser)
        .where(
            SystemUser.id == user_id,
            SystemUser.is_active.is_(True),
        )
        .options(selectinload(SystemUser.role).selectinload(Role.permissions))
    )
    result = await db.execute(stmt)
    user_obj = result.scalar_one_or_none()

    if user_obj is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return _build_user_dict(user_obj)


async def _fetch_system_user_by_email(email: str, db: AsyncSession) -> Dict[str, Any]:
    """Query SystemUser + Role (with permissions) by email in one query.

    Raises HTTP 500 if no matching user is found (used for dev bypass only).
    """
    stmt = (
        select(SystemUser)
        .where(
            SystemUser.email == email,
            SystemUser.is_active.is_(True),
        )
        .options(selectinload(SystemUser.role).selectinload(Role.permissions))
    )
    result = await db.execute(stmt)
    user_obj = result.scalar_one_or_none()

    if user_obj is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No SuperAdmin user found in database. Please run initialization.",
        )

    return _build_user_dict(user_obj)


def _build_user_dict(user_obj: SystemUser) -> Dict[str, Any]:
    """Serialise a SystemUser ORM object, strip password_hash, and attach role
    with permissions using the already eagerly loaded relationships."""
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
    """Resolve the authenticated SystemUser from a JWT token.

    Dev bypass
    ----------
    When ``settings.ENABLE_JWT`` is False (non-production only) the token is
    ignored and the SuperAdmin account is returned directly from the database.

    The returned dict includes ``user['role']['permissions']`` as a list of
    permission codenames (e.g. ``["system:manage", "billing:manage"]``).
    """
    if not settings.ENABLE_JWT:
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="JWT must be enabled in production",
            )
        user_dict = await _fetch_system_user_by_email(settings.SUPERADMIN_EMAIL, db)
        user_dict["user_type"] = "system"
        return user_dict

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    user_type = payload.get("user_type")
    if user_type != "system":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System access required",
        )

    user_dict = await _fetch_system_user_by_id(user_id, db)
    user_dict["user_type"] = "system"
    return user_dict


async def get_current_user(
    token: str = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Generic current-user dependency for dino-system.

    dino-system only hosts system users, so this always resolves a SystemUser.
    The dev bypass follows the same rules as ``get_current_system_user``.
    The returned dict includes ``user['role']['permissions']`` as a list of
    permission codenames.
    """
    if not settings.ENABLE_JWT:
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="JWT must be enabled in production",
            )
        user_dict = await _fetch_system_user_by_email(settings.SUPERADMIN_EMAIL, db)
        user_dict["user_type"] = "system"
        return user_dict

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    user_type = payload.get("user_type")
    if not user_type or user_type != "system":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System access required",
        )

    user_dict = await _fetch_system_user_by_id(user_id, db)
    user_dict["user_type"] = "system"
    return user_dict
