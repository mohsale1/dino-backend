from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.User import ApplicationUserService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.schemas.User import UserCreate, UserUpdate

router = APIRouter(prefix="/users", tags=["Application Users"])


class UpdateRoleRequest(BaseModel):
    role_id: int


def _assert_same_workspace(current_user: Dict[str, Any], target_user: Dict[str, Any]) -> None:
    """Raise 404 if caller attempts to access a user outside their workspace."""
    caller_workspace_id = current_user.get("workspace_id")
    if target_user.get("workspace_id") != caller_workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.get("", response_model=BaseResponse)
async def get_all_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    persona_id: Optional[int] = Query(None),
    role_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated application users scoped to the caller's workspace."""
    service = ApplicationUserService(db)

    workspace_id = current_user.get("workspace_id")
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to a workspace",
        )

    items, total, total_pages = await service.get_paginated_users(
        workspace_id=workspace_id,
        persona_id=persona_id,
        role_id=role_id,
        search_query=search,
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


@router.post("", response_model=BaseResponse)
async def create_user(
    user: UserCreate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new application user."""
    service = ApplicationUserService(db)

    workspace_id = current_user.get("workspace_id")
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to a workspace",
        )

    if await service.email_exists(user.email, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered in this workspace",
        )

    if not await service.validate_application_role(user.role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not an application role (role_type must be 1)",
        )

    user_data = user.model_dump()
    user_data["workspace_id"] = workspace_id  # enforce caller's workspace

    created = await service.create_user(user_data)
    return {
        "success": True,
        "message": "User created successfully",
        "data": created,
    }


# NOTE: Static sub-path /role/{role_id} must be declared before /{user_id}
# to prevent FastAPI matching "role" as a user_id integer.
@router.get("/role/{role_id}", response_model=BaseResponse)
async def get_users_by_role(
    role_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get all users with a specific role in the caller's workspace."""
    service = ApplicationUserService(db)
    workspace_id = current_user.get("workspace_id")
    users = await service.get_users_by_role(role_id, workspace_id=workspace_id)
    return {"success": True, "message": "Users retrieved successfully", "data": users}


@router.get("/{user_id}", response_model=BaseResponse)
async def get_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get user details."""
    service = ApplicationUserService(db)
    user = await service.get_user_with_role(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _assert_same_workspace(current_user, user)
    return {"success": True, "message": "User retrieved successfully", "data": user}


@router.put("/{user_id}", response_model=BaseResponse)
async def update_user(
    user_id: int,
    user: UserUpdate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update user."""
    service = ApplicationUserService(db)
    existing = await service.get_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _assert_same_workspace(current_user, existing)

    data = user.model_dump(exclude_unset=True)
    if "role_id" in data and not await service.validate_application_role(data["role_id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not an application role",
        )

    success = await service.update_user(user_id, data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"success": True, "message": "User updated successfully"}


@router.delete("/{user_id}", response_model=BaseResponse)
async def delete_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete user."""
    service = ApplicationUserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _assert_same_workspace(current_user, user)
    success = await service.soft_delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"success": True, "message": "User deleted successfully"}


@router.post("/{user_id}/restore", response_model=BaseResponse)
async def restore_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:update")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted user."""
    service = ApplicationUserService(db)
    user = await service.get_by_id(user_id, include_deleted=True)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _assert_same_workspace(current_user, user)
    if user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not deleted",
        )
    success = await service.restore_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"success": True, "message": "User restored successfully"}


@router.put("/{user_id}/role", response_model=BaseResponse)
async def update_user_role(
    user_id: int,
    request: UpdateRoleRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update user role."""
    service = ApplicationUserService(db)
    existing = await service.get_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _assert_same_workspace(current_user, existing)
    if not await service.validate_application_role(request.role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not an application role",
        )
    success = await service.update_user(user_id, {"role_id": request.role_id})
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"success": True, "message": "User role updated successfully"}
