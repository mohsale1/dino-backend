from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.schemas.SystemUser import SystemUserCreate, SystemUserUpdate
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.User import SystemUserService

router = APIRouter(prefix="/users", tags=["System Users"])


@router.post("", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('users:create'))])
async def create_system_user(user: SystemUserCreate, db: AsyncSession = Depends(get_db)):
    """Create new system user"""
    service = SystemUserService(db)

    if await service.email_exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    if not await service.validate_system_role(user.role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not a system role (role_type must be 0)"
        )

    user_data = await service.create_system_user(user.model_dump())

    return {
        "success": True,
        "message": "System user created successfully",
        "data": {"id": user_data.get("id") if isinstance(user_data, dict) else user_data}
    }


@router.get("", dependencies=[Depends(SystemPermissionCheck.require('users:read'))])
async def get_all_system_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    order_by: str = Query("created_at"),
    order_direction: str = Query("desc"),
    active_only: bool = Query(True, description="True = active users only, False = all users"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    db: AsyncSession = Depends(get_db)
):
    """Get all system users with pagination"""
    service = SystemUserService(db)

    if page_size > 100:
        page_size = 100

    items, total, total_pages = await service.get_paginated_users(
        page=page,
        page_size=page_size,
        active_only=active_only,
        search_query=search,
        order_by=order_by,
        order_direction=order_direction,
    )

    return {
        "success": True,
        "message": "System users retrieved successfully",
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


@router.get("/role/{role_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('users:read'))])
async def get_users_by_role(role_id: int, db: AsyncSession = Depends(get_db)):
    """Get all users with a specific role"""
    service = SystemUserService(db)
    users = await service.get_users_by_role(role_id)
    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": users
    }


@router.get("/{user_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('users:read'))])
async def get_system_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get system user details"""
    service = SystemUserService(db)
    user = await service.get_user_with_role(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {
        "success": True,
        "message": "User retrieved successfully",
        "data": user
    }


@router.put("/{user_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('users:update'))])
async def update_system_user(user_id: str, user: SystemUserUpdate, db: AsyncSession = Depends(get_db)):
    """Update system user"""
    service = SystemUserService(db)

    success = await service.update_user(user_id, user.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"success": True, "message": "User updated successfully"}


@router.delete("/{user_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('users:delete'))])
async def delete_system_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete system user.
    Sets is_active = False. Record is permanently retained.
    """
    service = SystemUserService(db)

    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already deactivated"
        )

    success = await service.delete_user(user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"success": True, "message": "User deleted successfully"}


@router.put("/{user_id}/role", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('users:manage'))])
async def update_user_role(user_id: str, role_id: int = Body(...), db: AsyncSession = Depends(get_db)):
    """Update user role"""
    service = SystemUserService(db)

    if not await service.validate_system_role(role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not a system role (role_type must be 0)"
        )

    success = await service.update_user(user_id, {"role_id": role_id})

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"success": True, "message": "User role updated successfully"}


@router.put("/{user_id}/activate", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('users:update'))])
async def activate_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Activate system user"""
    service = SystemUserService(db)

    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    success = await service.update_user(user_id, {"is_active": True})

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"success": True, "message": "User activated successfully"}


@router.put("/{user_id}/deactivate", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('users:update'))])
async def deactivate_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Deactivate system user"""
    service = SystemUserService(db)

    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    success = await service.update_user(user_id, {"is_active": False})

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"success": True, "message": "User deactivated successfully"}
