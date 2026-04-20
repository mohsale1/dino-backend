from fastapi import APIRouter, Body, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.Role import RoleCreate, RoleUpdate, RoleResponse
from src.system.services.Role import RoleService
from src.base.BaseSchema import BaseResponse
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.config.Database import get_db
from typing import List, Dict, Any

router = APIRouter(prefix="/roles", tags=["System Roles"])

@router.post("", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('roles:create'))])
async def create_role(role: RoleCreate, db: AsyncSession = Depends(get_db)):
    """Create new role"""
    service = RoleService(db)

    # Check if role already exists
    if await service.role_exists(role.name, role.role_type):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role '{role.name}' already exists for role_type {role.role_type}"
        )

    role_id = await service.create_role(role.model_dump())

    return {
        "success": True,
        "message": "Role created successfully",
        "data": {"id": role_id}
    }

@router.get("", dependencies=[Depends(SystemPermissionCheck.require('roles:read'))])
async def get_all_roles(
    page: int = 1,
    page_size: int = 10,
    role_type: int = None,
    order_by: str = "created_at",
    order_direction: str = "desc",
    db: AsyncSession = Depends(get_db)
):
    """
    Get all roles with pagination

    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - role_type: Filter by role type (0=System, 1=Application)
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    """
    from src.base.BaseSchema import PaginatedResponse, PaginationMeta

    service = RoleService(db)

    if role_type is not None and role_type not in [0, 1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_type must be 0 (System) or 1 (Application)"
        )

    # Validate page_size
    if page_size > 100:
        page_size = 100

    filters = {"role_type": role_type} if role_type is not None else None

    items, total, total_pages = await service.get_paginated(
        page=page,
        page_size=page_size,
        filters=filters,
        order_by=order_by,
        order_direction=order_direction
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
            "has_prev": page > 1
        }
    }

@router.get("/system", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('roles:read'))])
async def get_system_roles(db: AsyncSession = Depends(get_db)):
    """Get all system roles (role_type=0)"""
    service = RoleService(db)

    roles = await service.get_roles_by_type(0)

    return {
        "success": True,
        "message": "System roles retrieved successfully",
        "data": roles
    }

@router.get("/application", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('roles:read'))])
async def get_application_roles(db: AsyncSession = Depends(get_db)):
    """Get all application roles (role_type=1)"""
    service = RoleService(db)

    roles = await service.get_roles_by_type(1)

    return {
        "success": True,
        "message": "Application roles retrieved successfully",
        "data": roles
    }

@router.get("/{role_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('roles:read'))])
async def get_role(role_id: int, db: AsyncSession = Depends(get_db)):
    """Get role details"""
    service = RoleService(db)

    role = await service.get_role_by_id(role_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    return {
        "success": True,
        "message": "Role retrieved successfully",
        "data": role
    }

@router.put("/{role_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('roles:update'))])
async def update_role(role_id: int, role: RoleUpdate, db: AsyncSession = Depends(get_db)):
    """Update role"""
    service = RoleService(db)

    # Check if role exists
    existing_role = await service.get_role_by_id(role_id)
    if not existing_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # If updating name, check for conflicts
    if role.name and role.name != existing_role.get('name'):
        if await service.role_exists(role.name, existing_role.get('role_type')):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role '{role.name}' already exists"
            )

    success = await service.update_role(role_id, role.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    return {
        "success": True,
        "message": "Role updated successfully"
    }

@router.delete("/{role_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('roles:delete'))])
async def delete_role(role_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete role - Data is preserved"""
    service = RoleService(db)

    # Check if role exists
    role = await service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Check if role is in use
    if await service.is_role_in_use(role_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete role that is assigned to users. Please reassign users first."
        )

    success = await service.soft_delete_role(role_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    return {
        "success": True,
        "message": "Role soft deleted successfully (data preserved)"
    }

@router.post("/{role_id}/permissions", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('roles:manage'))])
async def add_permissions(role_id: int, permissions: List[str] = Body(...), db: AsyncSession = Depends(get_db)):
    """Add permissions to role"""
    service = RoleService(db)

    success = await service.add_permissions(role_id, permissions)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    return {
        "success": True,
        "message": "Permissions added successfully"
    }

@router.delete("/{role_id}/permissions", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('roles:manage'))])
async def remove_permissions(role_id: int, permissions: List[str] = Body(...), db: AsyncSession = Depends(get_db)):
    """Remove permissions from role"""
    service = RoleService(db)

    success = await service.remove_permissions(role_id, permissions)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    return {
        "success": True,
        "message": "Permissions removed successfully"
    }

@router.put("/{role_id}/restore", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('roles:restore'))])
async def restore_role(role_id: int, db: AsyncSession = Depends(get_db)):
    """Restore a soft-deleted role"""
    service = RoleService(db)

    # Check if role exists (including deleted)
    role = await service.get_role_by_id(role_id, include_deleted=True)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    if role.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role is not deleted"
        )

    success = await service.restore_role(role_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    return {
        "success": True,
        "message": "Role restored successfully"
    }

@router.get("/{role_id}/users", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('roles:read'))])
async def get_role_users(role_id: int, db: AsyncSession = Depends(get_db)):
    """Get all users assigned to a role"""
    service = RoleService(db)

    # Check if role exists
    role = await service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    users = await service.get_users_by_role(role_id)

    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": {
            "role": role,
            "users": users,
            "count": len(users)
        }
    }
