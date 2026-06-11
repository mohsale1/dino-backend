"""
Users router — CRUD for application users (user_type=1).
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.User import ApplicationUserService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import (
    BadRequestError,
    EmailAlreadyExistsError,
    InvalidRoleError,
    NotFoundError,
    UserNotDeletedError,
)
from src.schemas.User import UserCreate, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Application Users"])


class UpdateRoleRequest(BaseModel):
    role_id: int = Field(..., ge=1)


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=BaseResponse)
async def get_me(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return the currently authenticated user with role."""
    user_id = current_user.get("id")
    logger.info("users.me.request user_id=%s", user_id)

    user = await ApplicationUserService(db).get_user_with_role(user_id)
    if not user:
        raise NotFoundError("User not found")

    logger.info("users.me.response user_id=%s", user_id)
    return {"success": True, "message": "User retrieved successfully", "data": user}


# ---------------------------------------------------------------------------
# GET /users/me/data
# ---------------------------------------------------------------------------

@router.get("/me/data", response_model=BaseResponse)
async def get_me_data(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return the currently authenticated user with role + linked personas (single batch query)."""
    user_id = current_user.get("id")
    logger.info("users.me_data.request user_id=%s", user_id)

    data = await ApplicationUserService(db).get_user_with_personas(user_id)
    if not data:
        raise NotFoundError("User not found")

    logger.info(
        "users.me_data.response user_id=%s personas=%s",
        user_id, len(data.get("personas", [])),
    )
    return {"success": True, "message": "User data retrieved successfully", "data": data}


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_all_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    workspace_id: Optional[int] = Query(None, ge=1),
    persona_id: Optional[int] = Query(None, ge=1),
    role_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
    include_deleted: bool = Query(False),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated application users."""
    user_id = current_user.get("id")
    logger.info(
        "users.list.request user_id=%s workspace_id=%s persona_id=%s "
        "role_id=%s search=%r page=%s page_size=%s include_deleted=%s",
        user_id, workspace_id, persona_id, role_id, search, page, page_size, include_deleted,
    )

    items, total, total_pages = await ApplicationUserService(db).get_paginated_users(
        workspace_id=workspace_id,
        persona_id=persona_id,
        role_id=role_id,
        search_query=search,
        page=page,
        page_size=page_size,
        include_deleted=include_deleted,
    )

    logger.info(
        "users.list.response user_id=%s total=%s page=%s returned=%s",
        user_id, total, page, len(items),
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


# ---------------------------------------------------------------------------
# POST /users
# ---------------------------------------------------------------------------

@router.post("", response_model=BaseResponse, status_code=201)
async def create_user(
    user: UserCreate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Create a new application user."""
    actor_id = current_user.get("id")
    logger.info(
        "users.create.request actor_id=%s email=%s role_id=%s",
        actor_id, user.email, user.role_id,
    )

    service = ApplicationUserService(db)

    if await service.email_exists(user.email):
        logger.warning("users.create.email_exists actor_id=%s email=%s", actor_id, user.email)
        raise EmailAlreadyExistsError()

    if not await service.validate_application_role(user.role_id):
        logger.warning("users.create.invalid_role actor_id=%s role_id=%s", actor_id, user.role_id)
        raise InvalidRoleError()

    created = await service.create_user(user.model_dump())

    logger.info(
        "users.create.response actor_id=%s user_id=%s email=%s",
        actor_id, created.get("id"), user.email,
    )
    return {"success": True, "message": "User created successfully", "data": created}


# ---------------------------------------------------------------------------
# GET /users/role/{role_id}
# ---------------------------------------------------------------------------

@router.get("/role/{role_id}", response_model=BaseResponse)
async def get_users_by_role(
    role_id: int,
    workspace_id: Optional[int] = Query(None, ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get all users with a specific role."""
    user_id = current_user.get("id")
    logger.info(
        "users.by_role.request user_id=%s role_id=%s workspace_id=%s",
        user_id, role_id, workspace_id,
    )

    users = await ApplicationUserService(db).get_users_by_role(role_id, workspace_id=workspace_id)

    logger.info(
        "users.by_role.response user_id=%s role_id=%s returned=%s",
        user_id, role_id, len(users),
    )
    return {"success": True, "message": "Users retrieved successfully", "data": users}


# ---------------------------------------------------------------------------
# GET /users/{user_id}
# ---------------------------------------------------------------------------

@router.get("/{user_id}", response_model=BaseResponse)
async def get_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get user details with role."""
    actor_id = current_user.get("id")
    logger.info("users.get.request actor_id=%s user_id=%s", actor_id, user_id)

    user = await ApplicationUserService(db).get_user_with_role(user_id)
    if not user:
        logger.warning("users.get.not_found actor_id=%s user_id=%s", actor_id, user_id)
        raise NotFoundError("User not found")

    logger.info("users.get.response actor_id=%s user_id=%s", actor_id, user_id)
    return {"success": True, "message": "User retrieved successfully", "data": user}


# ---------------------------------------------------------------------------
# PUT /users/{user_id}
# ---------------------------------------------------------------------------

@router.put("/{user_id}", response_model=BaseResponse)
async def update_user(
    user_id: int,
    user: UserUpdate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update user fields."""
    actor_id = current_user.get("id")
    data = user.model_dump(exclude_unset=True)

    if not data:
        logger.warning("users.update.empty_payload actor_id=%s user_id=%s", actor_id, user_id)
        raise BadRequestError("No fields provided for update")

    logger.info(
        "users.update.request actor_id=%s user_id=%s fields=%s",
        actor_id, user_id, list(data.keys()),
    )

    service = ApplicationUserService(db)

    if "role_id" in data and not await service.validate_application_role(data["role_id"]):
        logger.warning("users.update.invalid_role actor_id=%s role_id=%s", actor_id, data["role_id"])
        raise InvalidRoleError()

    success = await service.update_user(user_id, data)
    if not success:
        logger.warning("users.update.not_found actor_id=%s user_id=%s", actor_id, user_id)
        raise NotFoundError("User not found")

    logger.info(
        "users.update.response actor_id=%s user_id=%s fields=%s",
        actor_id, user_id, list(data.keys()),
    )
    return {"success": True, "message": "User updated successfully"}


# ---------------------------------------------------------------------------
# DELETE /users/{user_id}
# ---------------------------------------------------------------------------

@router.delete("/{user_id}", response_model=BaseResponse)
async def delete_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a user."""
    actor_id = current_user.get("id")
    logger.info("users.delete.request actor_id=%s user_id=%s", actor_id, user_id)

    success = await ApplicationUserService(db).soft_delete_user(user_id)
    if not success:
        logger.warning("users.delete.not_found actor_id=%s user_id=%s", actor_id, user_id)
        raise NotFoundError("User not found")

    logger.info("users.delete.response actor_id=%s user_id=%s", actor_id, user_id)
    return {"success": True, "message": "User deleted successfully"}


# ---------------------------------------------------------------------------
# POST /users/{user_id}/restore
# ---------------------------------------------------------------------------

@router.post("/{user_id}/restore", response_model=BaseResponse)
async def restore_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted user."""
    actor_id = current_user.get("id")
    logger.info("users.restore.request actor_id=%s user_id=%s", actor_id, user_id)

    service = ApplicationUserService(db)
    user = await service.get_by_id(user_id, include_deleted=True)
    if not user:
        logger.warning("users.restore.not_found actor_id=%s user_id=%s", actor_id, user_id)
        raise NotFoundError("User not found")
    if user.get("is_active", False):
        raise UserNotDeletedError()

    await service.restore_user(user_id)

    logger.info("users.restore.response actor_id=%s user_id=%s", actor_id, user_id)
    return {"success": True, "message": "User restored successfully"}


# ---------------------------------------------------------------------------
# PUT /users/{user_id}/role
# ---------------------------------------------------------------------------

@router.put("/{user_id}/role", response_model=BaseResponse)
async def update_user_role(
    user_id: int,
    request: UpdateRoleRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update user role."""
    actor_id = current_user.get("id")
    logger.info(
        "users.role.update.request actor_id=%s user_id=%s role_id=%s",
        actor_id, user_id, request.role_id,
    )

    service = ApplicationUserService(db)

    if not await service.validate_application_role(request.role_id):
        logger.warning(
            "users.role.update.invalid_role actor_id=%s role_id=%s",
            actor_id, request.role_id,
        )
        raise InvalidRoleError()

    success = await service.update_user(user_id, {"role_id": request.role_id})
    if not success:
        logger.warning("users.role.update.not_found actor_id=%s user_id=%s", actor_id, user_id)
        raise NotFoundError("User not found")

    logger.info(
        "users.role.update.response actor_id=%s user_id=%s role_id=%s",
        actor_id, user_id, request.role_id,
    )
    return {"success": True, "message": "User role updated successfully"}
