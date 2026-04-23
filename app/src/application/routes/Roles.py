"""
Roles router — read-only access to application roles.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.repositories.RoleRepository import RoleRepository

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=BaseResponse)
async def get_roles(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("roles:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get all application roles (role_type=1)."""
    repo = RoleRepository(db)
    roles = await repo.get_by_type(role_type=1)
    return {"success": True, "message": "Roles retrieved successfully", "data": roles}


@router.get("/{role_id}", response_model=BaseResponse)
async def get_role(
    role_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("roles:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get an application role by ID."""
    repo = RoleRepository(db)
    role = await repo.get_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return {"success": True, "message": "Role retrieved successfully", "data": role}
