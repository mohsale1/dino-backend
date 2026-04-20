from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from src.schemas.ApplicationUser import ApplicationUserCreate, ApplicationUserUpdate, ApplicationUserResponse
from src.application.services.User import ApplicationUserService
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationRoleCheck
from src.core.Dependencies import get_current_application_user
from typing import Dict, Any, Optional

router = APIRouter(prefix="/users", tags=["Application Users"])


class UpdateRoleRequest(BaseModel):
    role_id: str


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
async def get_current_user_data(current_user: Dict[str, Any] = Depends(get_current_application_user)):
    """Get current application user data with workspace and organization details"""
    from src.repositories.UserRepository import UserRepository
    from src.repositories.WorkspaceRepository import WorkspaceRepository
    from src.repositories.OrganizationRepository import OrganizationRepository

    user_repo = UserRepository('application_users')
    workspace_repo = WorkspaceRepository()
    org_repo = OrganizationRepository()

    user_id = current_user.get('id')
    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    workspace = None
    if user.get('workspace_id'):
        workspace = workspace_repo.get_by_id(user['workspace_id'])

    venue = None
    if user.get('organization_id'):
        venue = org_repo.get_by_id(user['organization_id'])

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
                "venue_ids": [user.get('organization_id')] if user.get('organization_id') else [],
                "is_active": user.get('is_active', True),
                "created_at": user.get('created_at'),
                "updated_at": user.get('updated_at')
            },
            "workspace": workspace,
            "venue": venue
        }
    }


@router.post("", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def create_application_user(
    user: ApplicationUserCreate,
    current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin_or_superadmin)
):
    """Create new application user (Admin, SuperAdmin)"""
    service = ApplicationUserService()

    if service.email_exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    if not service.validate_application_role(user.role_id):
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

    user_id = service.create_application_user(user_data)

    return {
        "success": True,
        "message": "Application user created successfully",
        "data": {"id": user_id}
    }


@router.get("", dependencies=[Depends(ApplicationRoleCheck.require_manager_or_superadmin)])
async def get_all_application_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    workspace_id: Optional[str] = Query(None, description="Filter by workspace (SuperAdmin only)"),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    role_id: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Order direction (asc/desc)"),
    include_deleted: bool = Query(False, description="Include soft-deleted users"),
    current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_manager_or_superadmin)
):
    """
    Get all application users with pagination (Admin, Manager, SuperAdmin).

    Application users (any role) are always scoped to their own workspace.
    Only SuperAdmin (system user) may query across workspaces.
    """
    service = ApplicationUserService()

    if page_size > 100:
        page_size = 100

    filters = {}
    user_type = current_user.get('user_type', 'application')

    if user_type == 'system':
        # SuperAdmin: optionally filter by workspace / organization
        if workspace_id:
            filters['workspace_id'] = workspace_id
        if organization_id:
            filters['organization_id'] = organization_id
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
        filters['workspace_id'] = caller_workspace_id

        # organization_id may further narrow results within the same workspace
        if organization_id:
            filters['organization_id'] = organization_id

    if role_id:
        filters['role_id'] = role_id
    if is_active is not None:
        filters['is_active'] = is_active

    items, total, total_pages = service.get_paginated_users(
        page=page,
        page_size=page_size,
        filters=filters if filters else None,
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


# NOTE: All static-segment routes (/role/{...}, /workspace/{...}, /organization/{...})
# MUST be declared before /{user_id} so FastAPI does not swallow them as user_id values.

@router.get("/role/{role_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def get_users_by_role(
    role_id: str,
    current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin_or_superadmin)
):
    """Get all users with a specific role, scoped to the caller's workspace (Admin only)"""
    service = ApplicationUserService()

    user_type = current_user.get('user_type', 'application')
    workspace_id = None if user_type == 'system' else current_user.get('workspace_id')

    users = service.get_users_by_role(role_id, workspace_id=workspace_id)

    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": users
    }


@router.get("/workspace/{workspace_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def get_users_by_workspace(
    workspace_id: str,
    current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin_or_superadmin)
):
    """Get all users in a workspace (SuperAdmin unrestricted; application users restricted to own workspace)"""
    service = ApplicationUserService()

    user_type = current_user.get('user_type', 'application')
    if user_type != 'system':
        caller_workspace_id = current_user.get('workspace_id')
        if workspace_id != caller_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to other workspaces is not allowed"
            )

    users = service.get_users_by_workspace(workspace_id)

    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": users
    }


@router.get("/organization/{organization_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_manager_or_superadmin)])
async def get_users_by_organization(
    organization_id: str,
    current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_manager_or_superadmin)
):
    """Get all users in an organization, scoped to the caller's workspace (Admin, Manager)"""
    service = ApplicationUserService()

    user_type = current_user.get('user_type', 'application')
    workspace_id = None if user_type == 'system' else current_user.get('workspace_id')

    users = service.get_users_by_organization(organization_id, workspace_id=workspace_id)

    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": users
    }


@router.get("/{user_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_manager_or_superadmin)])
async def get_application_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_manager_or_superadmin)
):
    """Get application user details (Admin, Manager)"""
    service = ApplicationUserService()

    user = service.get_user_with_role(user_id)

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


@router.put("/{user_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def update_application_user(
    user_id: str,
    user: ApplicationUserUpdate,
    current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin_or_superadmin)
):
    """Update application user (Admin only)"""
    service = ApplicationUserService()

    existing_user = service.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, existing_user)

    update_data = user.model_dump(exclude_unset=True)
    if 'role_id' in update_data:
        if not service.validate_application_role(update_data['role_id']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role or role is not an application role (role_type must be 1)"
            )

    success = service.update_user(user_id, update_data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "success": True,
        "message": "User updated successfully"
    }


@router.delete("/{user_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def delete_application_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin_or_superadmin)
):
    """Soft delete application user (Admin only) - Data is preserved"""
    service = ApplicationUserService()

    user = service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, user)

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


@router.put("/{user_id}/restore", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def restore_application_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin_or_superadmin)
):
    """Restore a soft-deleted application user (Admin only)"""
    service = ApplicationUserService()

    user = service.get_by_id(user_id, include_deleted=True)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, user)

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


@router.put("/{user_id}/activate", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def activate_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin_or_superadmin)
):
    """Activate application user (Admin only)"""
    service = ApplicationUserService()

    existing_user = service.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, existing_user)

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


@router.put("/{user_id}/deactivate", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def deactivate_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin_or_superadmin)
):
    """Deactivate application user (Admin only)"""
    service = ApplicationUserService()

    existing_user = service.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, existing_user)

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


@router.put("/{user_id}/role", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def update_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin_or_superadmin)
):
    """Update user role (Admin only)"""
    service = ApplicationUserService()

    existing_user = service.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _assert_same_workspace(current_user, existing_user)

    if not service.validate_application_role(request.role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not an application role (role_type must be 1)"
        )

    success = service.update_user(user_id, {"role_id": request.role_id})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "success": True,
        "message": "User role updated successfully"
    }
