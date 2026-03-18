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

@router.get("/me/data", response_model=BaseResponse)
async def get_current_user_data(current_user: Dict[str, Any] = Depends(get_current_application_user)):
    """Get current application user data with workspace and organization details"""
    from src.repositories.UserRepository import UserRepository
    from src.repositories.WorkspaceRepository import WorkspaceRepository
    from src.repositories.OrganizationRepository import OrganizationRepository
    
    user_repo = UserRepository('application_users')
    workspace_repo = WorkspaceRepository()
    org_repo = OrganizationRepository()
    
    # Get full user details
    user_id = current_user.get('id')
    user = user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get workspace details
    workspace = None
    if user.get('workspace_id'):
        workspace = workspace_repo.get_by_id(user['workspace_id'])
    
    # Get organization (venue) details
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
async def create_application_user(user: ApplicationUserCreate, current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin_or_superadmin)):
    """Create new application user (Admin, SuperAdmin)"""
    service = ApplicationUserService()
    
    # Check if email already exists
    if service.email_exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Validate role exists and is an application role
    if not service.validate_application_role(user.role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role or role is not an application role (role_type must be 1)"
        )
    
    # Get workspace_id
    user_data = user.model_dump()
    user_type = current_user.get('user_type', 'application')
    
    # Determine workspace_id
    if user_type == 'system':
        # SuperAdmin can specify workspace_id in the request
        # If not provided, it's an error
        workspace_id = user_data.get('workspace_id')
        if not workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="workspace_id is required when creating application users as SuperAdmin"
            )
    else:
        # Application user - use their workspace_id
        workspace_id = current_user.get('workspace_id')
        if not workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to a workspace"
            )
        # Override any workspace_id in request with current user's workspace
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
    workspace_id: Optional[str] = Query(None, description="Filter by workspace"),
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
    Get all application users with pagination (Admin, Manager, SuperAdmin)
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - workspace_id: Filter by workspace
    - organization_id: Filter by organization
    - role_id: Filter by role
    - is_active: Filter by active status
    - search: Search by name or email
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    - include_deleted: Include soft-deleted users (default: false)
    """
    service = ApplicationUserService()
    
    # Validate page_size
    if page_size > 100:
        page_size = 100
    
    # Build filters based on user role and type
    filters = {}
    user_role = current_user.get('role', {}).get('name')
    user_type = current_user.get('user_type', 'application')
    
    # SuperAdmin (system users) can see all users
    if user_type == 'system' and user_role == 'SuperAdmin':
        # SuperAdmin can filter by workspace and organization
        if workspace_id:
            filters['workspace_id'] = workspace_id
        if organization_id:
            filters['organization_id'] = organization_id
    # Managers can only see users in their workspace
    elif user_role == 'Manager':
        filters['workspace_id'] = current_user.get('workspace_id')
        # If organization_id is provided, validate it belongs to their workspace
        if organization_id:
            filters['organization_id'] = organization_id
    elif user_role == 'Admin':
        # Admins can filter by workspace
        if workspace_id:
            filters['workspace_id'] = workspace_id
        if organization_id:
            filters['organization_id'] = organization_id
    
    # Add other filters
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

@router.get("/role/{role_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def get_users_by_role(role_id: str):
    """Get all users with specific role (Admin only)"""
    service = ApplicationUserService()

    users = service.get_users_by_role(role_id)

    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": users
    }

@router.get("/workspace/{workspace_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def get_users_by_workspace(workspace_id: str):
    """Get all users in a workspace (Admin only)"""
    service = ApplicationUserService()

    users = service.get_users_by_workspace(workspace_id)

    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": users
    }

@router.get("/organization/{organization_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_manager_or_superadmin)])
async def get_users_by_organization(organization_id: str, current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_manager_or_superadmin)):
    """Get all users in an organization (Admin, Manager)"""
    service = ApplicationUserService()

    # Check access based on role
    user_role = current_user.get('role', {}).get('name')

    if user_role == 'Manager':
        # Managers can only view users in their organization
        if organization_id != current_user.get('organization_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )

    users = service.get_users_by_organization(organization_id)

    return {
        "success": True,
        "message": "Users retrieved successfully",
        "data": users
    }

@router.get("/{user_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_manager_or_superadmin)])
async def get_application_user(user_id: str, current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_manager_or_superadmin)):
    """Get application user details (Admin, Manager)"""
    service = ApplicationUserService()
    
    user = service.get_user_with_role(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check access based on role
    user_role = current_user.get('role', {}).get('name')
    
    if user_role == 'Manager':
        # Managers can only view users in their workspace
        if user.get('workspace_id') != current_user.get('workspace_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this user"
            )
    
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
    
    # Check if user exists
    existing_user = service.get_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate role if being updated
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
async def delete_application_user(user_id: str, current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin_or_superadmin)):
    """Soft delete application user (Admin only) - Data is preserved"""
    service = ApplicationUserService()
    
    # Check if user exists
    user = service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deletion
    if user_id == current_user.get('id'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete your own account"
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

@router.put("/{user_id}/restore", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def restore_application_user(user_id: str):
    """Restore a soft-deleted application user (Admin only)"""
    service = ApplicationUserService()
    
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

@router.put("/{user_id}/activate", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin_or_superadmin)])
async def activate_user(user_id: str):
    """Activate application user (Admin only)"""
    service = ApplicationUserService()
    
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
async def deactivate_user(user_id: str, current_user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin_or_superadmin)):
    """Deactivate application user (Admin only)"""
    service = ApplicationUserService()
    
    # Prevent self-deactivation
    if user_id == current_user.get('id'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate your own account"
        )
    
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
async def update_user_role(user_id: str, request: UpdateRoleRequest):
    """Update user role (Admin only)"""
    service = ApplicationUserService()
    
    # Validate role exists and is an application role
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
