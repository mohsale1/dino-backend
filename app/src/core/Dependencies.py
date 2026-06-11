"""
FastAPI dependency functions for dino-application.

Resolves the authenticated application user (user_type=1) from a JWT token.
workspace_id is derived from user_personas → workspace_personas and injected
into the user dict so all downstream route code can read current_user["workspace_id"]
without any changes.

Both the user+role query and the workspace_id lookup run in parallel via asyncio.gather.
"""

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.Database import get_db
from src.core.Exceptions import NotAuthenticatedError, PermissionDeniedError
from src.core.Security import decode_token, get_current_user_token
from src.models.Role import Role
from src.models.User import User, user_personas
from src.models.Workspace import workspace_personas

if TYPE_CHECKING:
    from src.models.Permission import Permission


# Fields extracted from the User ORM object into the current_user dict
_USER_SAFE_FIELDS: tuple = (
    "id", "user_type", "email", "first_name", "last_name",
    "phone", "role_id", "last_login", "is_active", "created_at", "updated_at",
)


def _coerce_value(value: Any) -> Any:
    return float(value) if isinstance(value, Decimal) else value


def _build_permission_codenames(permissions: List["Permission"]) -> List[str]:
    return [
        f"{p.resource}:{p.action}"
        for p in permissions
        if p.resource and p.action
    ]


async def _fetch_user_with_role(user_id: int, db: AsyncSession) -> User:
    """Single query: User + Role + Permissions via selectinload."""
    stmt = (
        select(User)
        .where(User.id == user_id, User.is_active.is_(True), User.user_type == 1)
        .options(selectinload(User.role).selectinload(Role.permissions))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _resolve_workspace_id(user_id: int, db: AsyncSession) -> Optional[int]:
    """Derive workspace_id via user_personas → workspace_personas. Returns first match."""
    stmt = (
        select(workspace_personas.c.workspace_id)
        .join(user_personas, user_personas.c.persona_id == workspace_personas.c.persona_id)
        .where(user_personas.c.user_id == user_id)
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _fetch_application_user(user_id: int, db: AsyncSession) -> Dict[str, Any]:
    """
    Resolve user + role + permissions AND workspace_id in parallel (asyncio.gather).
    Raises NotAuthenticatedError if the user is not found or inactive.
    """
    user_obj, workspace_id = await asyncio.gather(
        _fetch_user_with_role(user_id, db),
        _resolve_workspace_id(user_id, db),
    )

    if user_obj is None:
        raise NotAuthenticatedError("User not found or inactive")

    user_dict: Dict[str, Any] = {
        field: _coerce_value(getattr(user_obj, field))
        for field in _USER_SAFE_FIELDS
    }
    user_dict["workspace_id"] = workspace_id

    role_obj = user_obj.role
    if role_obj is not None:
        user_dict["role"] = {
            "id": role_obj.id,
            "name": role_obj.name,
            "role_type": role_obj.role_type,
            "permissions": _build_permission_codenames(role_obj.permissions),
        }

    return user_dict


# --------------------------------------------------------------------------- #
# Public dependency                                                            #
# --------------------------------------------------------------------------- #

async def get_current_application_user(
    token: str = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Resolve the authenticated application user (user_type=1) from a JWT token."""
    payload = decode_token(token)

    if payload.get("user_type") != 1:
        raise PermissionDeniedError("Application access required")

    sub = payload.get("sub")
    if not sub:
        raise NotAuthenticatedError("Invalid token: missing subject")

    try:
        uid = int(sub)
    except (ValueError, TypeError):
        raise NotAuthenticatedError("Invalid token: subject is not a valid user ID")

    return await _fetch_application_user(uid, db)
