from fastapi import APIRouter, HTTPException, status, Depends
from src.schemas.SystemUser import SystemUserCreate, SystemUserUpdate, SystemUserResponse
from src.system.services.User import SystemUserService
from src.base.BaseSchema import BaseResponse
from src.system.middleware.RoleCheck import SystemRoleCheck
from typing import Dict, Any

router = APIRouter(prefix="/users", tags=["System Users"])

@router.post("", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def create_system_user(user: SystemUserCreate):
    """Create new system user (SuperAdmin only)"""
    service = SystemUserService()
    
    # Check if email already exists
    if service.email_exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Validate role exists and is a system role
    if not service.validate_system_role(user.role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not a system role (role_type must be 0)"
        )
    
    user_id = service.create_system_user(user.model_dump())
    
    return {
        "success": True,
        "message": "System user created successfully",
        "data": {"id": user_id}
    }

@router.get("", dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_all_system_users(
    page: int = 1,
    page_size: int = 10,
    order_by: str = "created_at",
    order_direction: str = "desc",
    include_deleted: bool = False
):
    """
    Get all system users with pagination (SuperAdmin only)
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    - include_deleted: Include soft-deleted users (default: false)
    """
    service = SystemUserService()
    
    # Validate page_size
    if page_size > 100:
        page_size = 100
    
    items, total, total_pages = service.get_paginated_users(
        page=page,
        page_size=page_size,
        include_deleted=include_deleted,
        order_by=order_by,
        order_direction=order_direction
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

@router.get("/{user_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_system_user(user_id: str):
    """Get system user details (SuperAdmin only)"""
    service = SystemUserService()
    
    user = service.get_user_with_role(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "success": True,
        "message": "User retrieved successfully",
        "data": user
    }

@router.put("/{user_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def update_system_user(user_id: str, user: SystemUserUpdate):
    """Update system user (SuperAdmin only)"""
    service = SystemUserService()
    
    success = service.update_user(user_id, user.model_dump(exclude_unset=True))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "success": True,
        "message": "User updated successfully"
    }

@router.delete("/{user_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def delete_system_user(user_id: str):
    """Soft delete system user (SuperAdmin only) - Data is preserved"""
    service = SystemUserService()
    
    # Check if user exists
    user = service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if it's a system user (auto-created)
    if user.get('is_system', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system users (auto-created SuperAdmin, etc.)"
        )
    
    success = service.soft_delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "success": True,
        "message": "User soft deleted successfully (data preserved)"
    }

@router.put("/{user_id}/restore", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def restore_system_user(user_id: str):
    """Restore a soft-deleted system user (SuperAdmin only)"""
    service = SystemUserService()
    
    # Check if user exists (including deleted)
    user = service.get_by_id(user_id, include_deleted=True)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.get('is_deleted', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not deleted"
        )
    
    success = service.restore_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "success": True,
        "message": "User restored successfully"
    }

@router.put("/{user_id}/role", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def update_user_role(user_id: str, role_id: str):
    """Update user role (SuperAdmin only)"""
    service = SystemUserService()
    
    # Validate role exists and is a system role
    if not service.validate_system_role(role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not a system role (role_type must be 0)"
        )
    
    success = service.update_user(user_id, {"role_id": role_id})
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "success": True,
        "message": "User role updated successfully"
    }

@router.put("/{user_id}/activate", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def activate_user(user_id: str):
    """Activate system user (SuperAdmin only)"""
    service = SystemUserService()
    
    success = service.update_user(user_id, {"is_active": True})
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "success": True,
        "message": "User activated successfully"
    }

@router.put("/{user_id}/deactivate", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def deactivate_user(user_id: str):
    """Deactivate system user (SuperAdmin only)"""
    service = SystemUserService()
    
    success = service.update_user(user_id, {"is_active": False})
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "success": True,
        "message": "User deactivated successfully"
    }

@router.get("/role/{role_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_users_by_role(role_id: str):
    """Get all users with specific role (SuperAdmin only)"""
    service = SystemUserService()
    
    users = service.get_users_by_role(role_id)
    
    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": users
    }