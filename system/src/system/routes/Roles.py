from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.schemas.Role import RoleCreate, RoleUpdate
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.Role import RoleService

router = APIRouter(prefix="/roles", tags=["System Roles"])


@router.get(
    "",
    dependencies=[Depends(SystemPermissionCheck.require("roles:list"))],
)
async def get_all_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role_type: Optional[int] = Query(None),
    order_by: str = Query("created_at"),
    order_direction: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    """Get all roles with pagination."""
    service = RoleService(db)

    if role_type is not None and role_type not in [0, 1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_type must be 0 (System) or 1 (Application)",
        )

    filters = {"role_type": role_type} if role_type is not None else None
    items, total, total_pages = await service.get_paginated(
        page=page,
        page_size=page_size,
        filters=filters,
        order_by=order_by,
        order_direction=order_direction,
    )
    return {
        "success": True,
        "message": "Roles retrieved successfully",
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


@router.post(
    "",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("roles:create"))],
)
async def create_role(role: RoleCreate, db: AsyncSession = Depends(get_db)):
    """Create a new role."""
    service = RoleService(db)
    if await service.role_exists(role.name, role.role_type):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{role.name}' already exists for role_type {role.role_type}",
        )
    created = await service.create_role(role.model_dump())
    return {
        "success": True,
        "message": "Role created successfully",
        "data": {"id": created.get("id")},
    }


@router.get(
    "/{role_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("roles:read"))],
)
async def get_role(role_id: int, db: AsyncSession = Depends(get_db)):
    """Get role details."""
    service = RoleService(db)
    role = await service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return {"success": True, "message": "Role retrieved successfully", "data": role}


@router.put(
    "/{role_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("roles:update"))],
)
async def update_role(role_id: int, role: RoleUpdate, db: AsyncSession = Depends(get_db)):
    """Update role."""
    service = RoleService(db)
    existing = await service.get_role_by_id(role_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.name and role.name != existing.get("name"):
        if await service.role_exists(role.name, existing.get("role_type")):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role '{role.name}' already exists",
            )
    success = await service.update_role(role_id, role.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return {"success": True, "message": "Role updated successfully"}


@router.delete(
    "/{role_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("roles:delete"))],
)
async def delete_role(role_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete role."""
    service = RoleService(db)
    role = await service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if await service.is_role_in_use(role_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete role that is assigned to users. Please reassign users first.",
        )
    success = await service.soft_delete_role(role_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return {"success": True, "message": "Role deleted successfully"}


@router.post(
    "/{role_id}/restore",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("roles:manage"))],
)
async def restore_role(role_id: int, db: AsyncSession = Depends(get_db)):
    """Restore a soft-deleted role."""
    service = RoleService(db)
    role = await service.get_role_by_id(role_id, include_deleted=True)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role is not deleted",
        )
    success = await service.restore_role(role_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return {"success": True, "message": "Role restored successfully"}


@router.post(
    "/{role_id}/permissions",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("roles:manage"))],
)
async def add_permissions(
    role_id: int,
    permission_ids: List[int] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """Add permissions to a role."""
    service = RoleService(db)
    await service.add_permissions(role_id, permission_ids)
    return {"success": True, "message": "Permissions added successfully"}


@router.delete(
    "/{role_id}/permissions",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("roles:manage"))],
)
async def remove_permissions(
    role_id: int,
    permission_ids: List[int] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """Remove permissions from a role."""
    service = RoleService(db)
    await service.remove_permissions(role_id, permission_ids)
    return {"success": True, "message": "Permissions removed successfully"}


@router.get(
    "/{role_id}/permissions",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("roles:read"))],
)
async def get_role_permissions(role_id: int, db: AsyncSession = Depends(get_db)):
    """Get permissions assigned to a role."""
    service = RoleService(db)
    permission_ids = await service.get_role_permissions(role_id)
    return {
        "success": True,
        "message": "Role permissions retrieved successfully",
        "data": permission_ids,
    }


@router.get(
    "/{role_id}/users",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("roles:read"))],
)
async def get_role_users(role_id: int, db: AsyncSession = Depends(get_db)):
    """Get all users assigned to a role."""
    service = RoleService(db)
    role = await service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    users = await service.get_users_by_role(role_id)
    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": {"role": role, "users": users, "count": len(users)},
    }
