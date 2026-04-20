from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.Database import get_db
from src.core.Security import decode_token, get_current_user_token
from src.models.Role import Role
from src.models.User import ApplicationUser


# --------------------------------------------------------------------------- #
# Whitelist of ApplicationUser columns safe to expose to callers               #
# --------------------------------------------------------------------------- #

_USER_SAFE_FIELDS: frozenset = frozenset([
    "id",
    "email",
    "first_name",
    "last_name",
    "phone",
    "role_id",
    "workspace_id",
    "last_login",
    "is_active",
    "created_at",
    "updated_at",
])


# --------------------------------------------------------------------------- #
# Internal helpers                                                             #
# --------------------------------------------------------------------------- #

def _coerce_value(value: Any) -> Any:
    """Apply type coercions for JSON-safe serialisation.

    - datetime -> ISO-8601 str
    - Decimal  -> float
    - everything else passes through unchanged
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _extract_permission_codenames(role_obj: Role) -> List[str]:
    """Return the list of permission codenames from an eagerly loaded Role.

    Reads the ``codename`` column directly from each Permission ORM object
    that was loaded via ``selectinload(Role.permissions)``.
    """
    return [
        perm.codename
        for perm in role_obj.permissions
        if perm.codename
    ]


async def _fetch_application_user(user_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Query ApplicationUser + Role + Permissions in a single round-trip.

    Uses ``selectinload`` to eagerly load ``role`` and then ``role.permissions``
    so that no additional queries are issued after the initial SELECT.

    Also stamps ``last_login`` on the user row as a fire-and-forget UPDATE
    (does not block the response — the session is flushed by FastAPI's
    dependency teardown).

    Raises HTTP 401 if the user does not exist or is soft-deleted
    (``is_active == False``).
    """
    stmt = (
        select(ApplicationUser)
        .where(
            ApplicationUser.id == user_id,
            ApplicationUser.is_active.is_(True),
        )
        .options(
            selectinload(ApplicationUser.role).selectinload(Role.permissions)
        )
    )
    result = await db.execute(stmt)
    user_obj = result.scalar_one_or_none()

    if user_obj is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Stamp last_login — single UPDATE, no extra SELECT needed.
    now = datetime.now(timezone.utc)
    await db.execute(
        update(ApplicationUser)
        .where(ApplicationUser.id == user_obj.id)
        .values(last_login=now)
        .execution_options(synchronize_session=False)
    )

    # Build user dict from whitelist only — no sensitive fields can leak.
    user_dict: Dict[str, Any] = {
        field: _coerce_value(getattr(user_obj, field, None))
        for field in _USER_SAFE_FIELDS
        if hasattr(user_obj, field)
    }
    # Reflect the just-written last_login value in the returned dict.
    user_dict["last_login"] = now.isoformat()

    # Attach role sub-dict with eagerly loaded permissions.
    role_obj: Role | None = user_obj.role
    if role_obj is not None:
        user_dict["role"] = {
            "id": role_obj.id,
            "name": role_obj.name,
            "role_type": role_obj.role_type,
            "permissions": _extract_permission_codenames(role_obj),
        }

    return user_dict


# --------------------------------------------------------------------------- #
# Public dependency functions                                                  #
# --------------------------------------------------------------------------- #

async def get_current_application_user(
    token: str = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Resolve the authenticated ApplicationUser from a JWT token.

    Rejects tokens whose ``user_type`` claim is not ``'application'`` with
    HTTP 403 — system tokens must never be accepted here.

    The returned dict includes ``user['role']['permissions']`` as a list of
    permission codenames (e.g. ``["categories:create", "orders:read"]``).
    """
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user_type = payload.get("user_type")
    if user_type != "application":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System tokens are not accepted by this service",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    user_dict = await _fetch_application_user(user_id, db)
    user_dict["user_type"] = "application"
    return user_dict


async def get_current_user(
    token: str = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Generic current-user dependency for dino-application.

    Validates that the ``user_type`` claim is ``'application'`` — system tokens
    are rejected with HTTP 403.  dino-application only hosts application users.

    The returned dict includes ``user['role']['permissions']`` as a list of
    permission codenames.
    """
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user_type = payload.get("user_type")
    if user_type != "application":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System tokens are not accepted by this service",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    user_dict = await _fetch_application_user(user_id, db)
    user_dict["user_type"] = "application"
    return user_dict
