"""
Roles router — read-only access to application roles (role_type=1).
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.schemas.roles import RoleResponse
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import NotFoundError
from src.repositories.RoleRepository import RoleRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=BaseResponse)
async def get_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("roles:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated application roles (role_type=1)."""
    roles = await RoleRepository(db).get_by_type(role_type=1)

    total = len(roles)
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    page_items = [
        {**role, "index": offset + idx + 1}
        for idx, role in enumerate(roles[offset: offset + page_size])
    ]

    return {
        "success": True,
        "message": "Roles retrieved successfully",
        "data": page_items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


@router.get("/{role_id}", response_model=BaseResponse)
async def get_role(
    role_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("roles:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get an application role by ID."""
    role = await RoleRepository(db).get_by_id(role_id)
    if not role:
        raise NotFoundError("Role not found")
    return {"success": True, "message": "Role retrieved successfully", "data": role}
