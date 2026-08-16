"""
Users router — CRUD for application users (user_type=1).
"""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.User import ApplicationUserService
from src.schemas.User import (
    UserCreate,
    UserUpdate,
    UpdateRoleRequest,
)
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import (
    BadRequestError,
    EmailAlreadyExistsError,
    InvalidRoleError,
    NotFoundError,
    UserNotDeletedError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Application Users"])


@router.get("/me", response_model=BaseResponse)
async def get_me(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:read")),
    db: AsyncSession = Depends(get_db),
):
    """Return the currently authenticated user with role."""
    user_id = current_user.get("id")
    user = await ApplicationUserService(db).get_user_with_role(user_id)
    if not user:
        raise NotFoundError("User not found")
    return {"success": True, "message": "User retrieved successfully", "data": user}


@router.get("/me/data", response_model=BaseResponse)
async def get_me_data(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:read")),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user with role + linked personas."""
    user_id = current_user.get("id")
    data = await ApplicationUserService(db).get_user_with_personas(user_id)
    if not data:
        raise NotFoundError("User not found")
    return {"success": True, "message": "User data retrieved successfully", "data": data}


@router.get("", response_model=BaseResponse)
async def get_all_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    workspace_id: Optional[int] = Query(None, ge=1),
    persona_id: Optional[int] = Query(None, ge=1),
    role_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
    include_deleted: bool = Query(False),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated application users."""
    items, total, total_pages = await ApplicationUserService(db).get_paginated_users(
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


@router.post("", response_model=BaseResponse, status_code=201)
async def create_user(
    user: UserCreate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new application user."""
    service = ApplicationUserService(db)
    if await service.email_exists(user.email):
        raise EmailAlreadyExistsError()
    if not await service.validate_application_role(user.role_id):
        raise InvalidRoleError()
    created = await service.create_user(user.model_dump())
    return {"success": True, "message": "User created successfully", "data": created}


@router.get("/role/{role_id}", response_model=BaseResponse)
async def get_users_by_role(
    role_id: int,
    workspace_id: Optional[int] = Query(None, ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get all users with a specific role."""
    users = await ApplicationUserService(db).get_users_by_role(role_id, workspace_id=workspace_id)
    return {"success": True, "message": "Users retrieved successfully", "data": users}


@router.get("/{user_id}", response_model=BaseResponse)
async def get_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get user details with role."""
    user = await ApplicationUserService(db).get_user_with_role(user_id)
    if not user:
        raise NotFoundError("User not found")
    return {"success": True, "message": "User retrieved successfully", "data": user}


@router.put("/{user_id}", response_model=BaseResponse)
async def update_user(
    user_id: int,
    user: UserUpdate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update user fields."""
    data = user.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestError("No fields provided for update")
    service = ApplicationUserService(db)
    if "role_id" in data and not await service.validate_application_role(data["role_id"]):
        raise InvalidRoleError()
    success = await service.update_user(user_id, data)
    if not success:
        raise NotFoundError("User not found")
    return {"success": True, "message": "User updated successfully"}


@router.delete("/{user_id}", response_model=BaseResponse)
async def delete_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a user."""
    success = await ApplicationUserService(db).soft_delete_user(user_id)
    if not success:
        raise NotFoundError("User not found")
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
        raise NotFoundError("User not found")
    if user.get("is_active", False):
        raise UserNotDeletedError()
    await service.restore_user(user_id)
    return {"success": True, "message": "User restored successfully"}


@router.put("/{user_id}/role", response_model=BaseResponse)
async def update_user_role(
    user_id: int,
    request: UpdateRoleRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("users:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update user role."""
    actor_id = current_user.get("id")
    logger.info(
        "users.role.update.request actor_id=%s user_id=%s role_id=%s",
        actor_id, user_id, request.role_id,
    )

    service = ApplicationUserService(db)

    # Validate role
    if not await service.validate_application_role(request.role_id):
        logger.warning(
            "users.role.update.invalid_role actor_id=%s role_id=%s",
            actor_id, request.role_id,
        )
        raise InvalidRoleError()

    # Update role
    success = await service.update_user(user_id, {"role_id": request.role_id})
    if not success:
        logger.warning("users.role.update.not_found actor_id=%s user_id=%s", actor_id, user_id)
        raise NotFoundError("User not found")

    logger.info(
        "users.role.update.response actor_id=%s user_id=%s role_id=%s",
        actor_id, user_id, request.role_id,
    )
    return {"success": True, "message": "User role updated successfully"}