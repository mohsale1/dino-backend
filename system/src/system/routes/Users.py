from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.schemas.User import UserCreate, UserUpdate
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.User import SystemUserService

router = APIRouter(prefix="/users", tags=["System Users"])


class UpdateRoleRequest(BaseModel):
    role_id: int


@router.get(
    "",
    dependencies=[Depends(SystemPermissionCheck.require("users:read"))],
)
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_type: Optional[int] = Query(None, description="0=System, 1=Application"),
    role_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated users."""
    service = SystemUserService(db)
    items, total, total_pages = await service.get_paginated_users(
        user_type=user_type,
        role_id=role_id,
        search=search,
        page=page,
        page_size=page_size,
        include_deleted=include_deleted,
    )
    return {
        "success": True,
        "message": "Users retrieved successfully",
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
    dependencies=[Depends(SystemPermissionCheck.require("users:create"))],
)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new system user."""
    service = SystemUserService(db)

    if await service.email_exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    if not await service.validate_system_role(user.role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not a system role (role_type must be 0)",
        )

    created = await service.create_user(user.model_dump())
    return {
        "success": True,
        "message": "User created successfully",
        "data": {"id": created.get("id")},
    }


# NOTE: Static sub-path /role/{role_id} must be declared before /{user_id}
# to prevent FastAPI matching "role" as a user_id integer.
@router.get(
    "/role/{role_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("users:read"))],
)
async def get_users_by_role(role_id: int, db: AsyncSession = Depends(get_db)):
    """Get all users with a specific role."""
    service = SystemUserService(db)
    users = await service.get_users_by_role(role_id)
    return {"success": True, "message": "Users retrieved successfully", "data": users}


@router.get(
    "/{user_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("users:read"))],
)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get user details."""
    service = SystemUserService(db)
    user = await service.get_user_with_role(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"success": True, "message": "User retrieved successfully", "data": user}


@router.put(
    "/{user_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("users:update"))],
)
async def update_user(user_id: int, user: UserUpdate, db: AsyncSession = Depends(get_db)):
    """Update user."""
    service = SystemUserService(db)
    success = await service.update_user(user_id, user.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"success": True, "message": "User updated successfully"}


@router.delete(
    "/{user_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("users:delete"))],
)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete user (sets is_active=False)."""
    service = SystemUserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already deactivated",
        )
    success = await service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"success": True, "message": "User deleted successfully"}


@router.post(
    "/{user_id}/restore",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("users:update"))],
)
async def restore_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Restore a soft-deleted user."""
    service = SystemUserService(db)
    user = await service.get_by_id(user_id, include_deleted=True)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not deleted",
        )
    success = await service.restore(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"success": True, "message": "User restored successfully"}


@router.put(
    "/{user_id}/role",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("users:update"))],
)
async def update_user_role(
    user_id: int,
    request: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update user role."""
    service = SystemUserService(db)
    if not await service.validate_system_role(request.role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not a system role (role_type must be 0)",
        )
    success = await service.update_user(user_id, {"role_id": request.role_id})
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"success": True, "message": "User role updated successfully"}
