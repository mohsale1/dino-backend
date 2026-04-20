from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.User import ApplicationUserService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.schemas.ApplicationUser import ApplicationUserCreate, ApplicationUserUpdate, ApplicationUserResponse

router = APIRouter(prefix="/users", tags=["Application Users"])


class UpdateRoleRequest(BaseModel):
    role_id: int


def _assert_same_workspace(current_user: Dict[str, Any], target_user: Dict[str, Any]) -> None:
    """
    Raise 404 if a non-SuperAdmin caller attempts to access a user that does
    not belong to their own workspace.  Using 404 (rather than 403) avoids
    leaking the existence of users in other workspaces.
    """
    if current_user.get('user_type', 'application') == 'system':
        return  # SuperAdmin has no workspace restriction
    caller_workspace_id = current_user.get('workspace_id')
    if target_user.get('workspace_id') != caller_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.get("/me/data", response_model=BaseResponse)
async def get_current_user_data(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db)
):
    """Get current application user data with workspace and persona details"""
    from src.repositories.WorkspaceRepository import WorkspaceRepository
    from src.repositories.PersonaRepository import PersonaRepository

    user_service = ApplicationUserService(db)
    workspace_repo = WorkspaceRepository(db)
    persona_repo = PersonaRepository(db)

    user_id = current_user.get('id')
    user = await user_service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    workspace = None
    if user.get('workspace_id'):
        workspace = await workspace_repo.get_by_id(user['workspace_id'])

    venue = None
    if user.get('persona_id'):
        venue = await persona_repo.get_by_id(user['persona_id'])

    return {
        "success": True,
        "message": "User data retrieved successfully",
        "data": {
            "user": {
                "id": user.get('id'),
                "email": user.get('email'),
                "first_name": user.get('first_name'),
                "last_name": user.get('last_name'),
                "phone": user.get('phone'),
                "role": current_user.get('role', {}).get('name', 'operator'),
                "venue_ids": [user.get('persona_id')] if user.get('persona_id') else [],
                "is_active": user.get('is_active', True),
                "created_at": user.get('created_at'),
                "updated_at": user.get('updated_at')
            },
            "workspace": workspace,
            "venue": venue
        }
    }


@router.post("", response_model=BaseResponse)
async def create_application_user(
    user: ApplicationUserCreate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('users:create')),
    db: AsyncSession = Depends(get_db)
):
    """Create new application user (Admin, SuperAdmin)"""
    service = ApplicationUserService(db)

    if await service.email_exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    if not await service.validate_application_role(user.role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not an application role (role_type must be 1)"
        )

    user_data = user.model_dump()
    user_type = current_user.get('user_type', 'application')

    if user_type == 'system':
        workspace_id = user_data.get('workspace_id')
        if not workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="workspace_id is required when creating application users as SuperAdmin"
            )
    else:
        workspace_id = current_user.get('workspace_id')
        if not workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to a workspace"
            )
        # Always enforce the caller's own workspace — ignore any workspace_id in the request body
        user_data['workspace_id'] = workspace_id

    user_id = await service.create_application_user(user_data)

    return {
        "success": True,
        "message": "Application user created successfully",
        "data": {"id": user_id}
    }


@router.get("")
async def get_all_application_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    workspace_id: Optional[int] = Query(None, description="Filter by workspace (SuperAdmin only)"),
    persona_id: Optional[int] = Query(None, description="Filter by persona"),
    role_id: Optional[int] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Order direction (asc/desc)"),
    include_deleted: bool = Query(False, description="Include soft-deleted users"),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('users:read')),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all application users with pagination (Admin, Manager, SuperAdmin).

    Application users (any role) are always scoped to their own workspace.
    Only SuperAdmin (system user) may query across workspaces.
    """
    service = ApplicationUserService(db)

    if page_size > 100:
        page_size = 100

    user_type = current_user.get('user_type', 'application')

    scoped_workspace_id = None
    scoped_persona_id = None
    scoped_role_id = role_id

    if user_type == 'system':
        # SuperAdmin: optionally filter by workspace / persona
        scoped_workspace_id = workspace_id or None
        scoped_persona_id = persona_id or None
    else:
        # All application users are strictly scoped to their own workspace.
        # The workspace_id query param is intentionally ignored to prevent
        # cross-workspace data leakage.
        caller_workspace_id = current_user.get('workspace_id')
        if not caller_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to a workspace"
            )
        scoped_workspace_id = caller_workspace_id

        # persona_id may further narrow results within the same workspace
        scoped_persona_id = persona_id or None

    items, total, total_pages = await service.get_paginated_users(
        page=page,
        page_size=page_size,
        workspace_id=scoped_workspace_id,
        persona_id=scoped_persona_id,
        role_id=scoped_role_id,
        search_query=search,
        include_deleted=include_deleted,
        order_by=order_by,
        order_direction=order_direction
    )

    return {
        "success": True,
        "message": "Application users retrieved successfully",
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


# NOTE: All static-segment routes (/role/{...}, /workspace/{...}, /persona/{...})
# MUST be declared before /{user_id} so FastAPI does not swallow them as user_id values.

@router.get("/role/{role_id}", response_model=BaseResponse)
async def get_users_by_role(
    role_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('users:read')),
    db: AsyncSession = Depends(get_db)
):
    """Get all users with a specific role, scoped to the caller's workspace (Admin only)"""
    service = ApplicationUserService(db)

    user_type = current_user.get('user_type', 'application')
    workspace_id = None if user_type == 'system' else current_user.get('workspace_id')

    users = await service.get_users_by_role(role_id, workspace_id=workspace_id)

    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": users
    }


@router.get("/workspace/{workspace_id}", response_model=BaseResponse)
async def get_users_by_workspace(
    workspace_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('users:read')),
    db: AsyncSession = Depends(get_db)
):
    """Get all users in a workspace (SuperAdmin unrestricted; application users restricted to own workspace)"""
    service = ApplicationUserService(db)

    user_type = current_user.get('user_type', 'application')
    if user_type != 'system':
        caller_workspace_id = current_user.get('workspace_id')
        if workspace_id != caller_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to other workspaces is not allowed"
            )

    users = await service.get_users_by_workspace(workspace_id)

    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": users
    }


@router.get("/persona/{persona_id}", response_model=BaseResponse)
async def get_users_by_persona(
    persona_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('users:read')),
    db: AsyncSession = Depends(get_db)
):
    """Get all users in a persona, scoped to the caller's workspace (Admin, Manager)"""
    service = ApplicationUserService(db)

    user_type = current_user.get('user_type', 'application')
    workspace_id = None if user_type == 'system' else current_user.get('workspace_id')

    users = await service.get_users_by_persona(persona_id, workspace_id=workspace_id)

    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": users
    }


@router.get("/{user_id}", response_model=BaseResponse)
async def get_application_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('users:read')),
    db: AsyncSession = Depends(get_db)
):
    """Get application user details (Admin, Manager)"""
    service = ApplicationUserService(db)

    user = await service.get_user_with_role(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, user)

    return {
        "success": True,
        "message": "User retrieved successfully",
        "data": user
    }


@router.put("/{user_id}", response_model=BaseResponse)
async def update_application_user(
    user_id: int,
    user: ApplicationUserUpdate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('users:update')),
    db: AsyncSession = Depends(get_db)
):
    """Update application user (Admin only)"""
    service = ApplicationUserService(db)

    existing_user = await service.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, existing_user)

    update_data = user.model_dump(exclude_unset=True)
    if 'role_id' in update_data:
        if not await service.validate_application_role(update_data['role_id']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role or role is not an application role (role_type must be 1)"
            )

    success = await service.update_user(user_id, update_data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "success": True,
        "message": "User updated successfully"
    }


@router.delete("/{user_id}", response_model=BaseResponse)
async def delete_application_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('users:delete')),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete application user (Admin only) - Data is preserved"""
    service = ApplicationUserService(db)

    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, user)

    success = await service.soft_delete_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "success": True,
        "message": "User soft deleted successfully (data preserved)"
    }


@router.put("/{user_id}/restore", response_model=BaseResponse)
async def restore_application_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('users:restore')),
    db: AsyncSession = Depends(get_db)
):
    """Restore a soft-deleted application user (Admin only)"""
    service = ApplicationUserService(db)

    user = await service.get_by_id(user_id, include_deleted=True)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, user)

    # is_active=True means active (not deleted); raise error if not deleted
    if user.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not deleted"
        )

    success = await service.restore_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "success": True,
        "message": "User restored successfully"
    }


@router.put("/{user_id}/activate", response_model=BaseResponse)
async def activate_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('users:update')),
    db: AsyncSession = Depends(get_db)
):
    """Activate application user (Admin only)"""
    service = ApplicationUserService(db)

    existing_user = await service.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, existing_user)

    success = await service.update_user(user_id, {"is_active": True})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "success": True,
        "message": "User activated successfully"
    }


@router.put("/{user_id}/deactivate", response_model=BaseResponse)
async def deactivate_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('users:update')),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate application user (Admin only)"""
    service = ApplicationUserService(db)

    existing_user = await service.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, existing_user)

    success = await service.update_user(user_id, {"is_active": False})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "success": True,
        "message": "User deactivated successfully"
    }


@router.put("/{user_id}/role", response_model=BaseResponse)
async def update_user_role(
    user_id: int,
    request: UpdateRoleRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('users:manage')),
    db: AsyncSession = Depends(get_db)
):
    """Update user role (Admin only)"""
    service = ApplicationUserService(db)

    existing_user = await service.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, existing_user)

    if not await service.validate_application_role(request.role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not an application role (role_type must be 1)"
        )

    success = await service.update_user(user_id, {"role_id": request.role_id})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "success": True,
        "message": "User role updated successfully"
    }
