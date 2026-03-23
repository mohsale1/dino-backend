from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.base.BaseSchema import BaseResponse
from src.system.middleware.RoleCheck import SystemRoleCheck
from src.system.services.Permission import PermissionService
from src.schemas.Permission import (
    PermissionCreate,
    PermissionUpdate,
    PermissionResponse,
    PermissionBulkCreate
)
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/permissions", tags=["System Permissions"])

# ==================== CRUD Collection Operations ====================

@router.post("", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def create_permission(permission: PermissionCreate):
    """
    Create new permission (SuperAdmin only)

    Creates a new permission in the system.
    """
    service = PermissionService()

    if service.permission_exists(permission.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Permission '{permission.name}' already exists"
        )

    permission_id = service.create_permission(permission.model_dump())

    return {
        "success": True,
        "message": "Permission created successfully",
        "data": {"id": permission_id}
    }

@router.get("", dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_all_permissions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category (system/application)"),
    resource: Optional[str] = Query(None, description="Filter by resource"),
    action: Optional[str] = Query(None, description="Filter by action"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Order direction (asc/desc)")
):
    """
    Get all permissions with pagination and filtering (SuperAdmin only)

    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - category: Filter by category (system/application)
    - resource: Filter by resource name
    - action: Filter by action type
    - is_active: Filter by active status
    - search: Search query for name/description
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    """
    service = PermissionService()

    if category and category not in ['system', 'application']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="category must be 'system' or 'application'"
        )

    if page_size > 100:
        page_size = 100

    items, total, total_pages = service.get_paginated_permissions(
        page=page,
        page_size=page_size,
        category=category,
        resource=resource,
        action=action,
        is_active=is_active,
        search_query=search,
        order_by=order_by,
        order_direction=order_direction
    )

    return {
        "success": True,
        "message": "Permissions retrieved successfully",
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

# ==================== Bulk Operations ====================

@router.post("/bulk", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def bulk_create_permissions(bulk_data: PermissionBulkCreate):
    """
    Bulk create permissions (SuperAdmin only)

    Creates multiple permissions at once.
    """
    service = PermissionService()

    names = [p.name for p in bulk_data.permissions]
    if len(names) != len(set(names)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate permission names in request"
        )

    existing = []
    for perm in bulk_data.permissions:
        if service.permission_exists(perm.name):
            existing.append(perm.name)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Permissions already exist: {', '.join(existing)}"
        )

    permissions_data = [p.model_dump() for p in bulk_data.permissions]
    permission_ids = service.bulk_create_permissions(permissions_data)

    return {
        "success": True,
        "message": f"{len(permission_ids)} permissions created successfully",
        "data": {
            "ids": permission_ids,
            "count": len(permission_ids)
        }
    }

# ==================== Query Operations ====================

@router.get("/category/{category}", dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_permissions_by_category(
    category: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """
    Get permissions by category with pagination (SuperAdmin only)

    Categories: system, application
    """
    service = PermissionService()

    if category not in ['system', 'application']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="category must be 'system' or 'application'"
        )

    items, total, total_pages = service.get_paginated_permissions(
        page=page,
        page_size=page_size,
        category=category
    )

    return {
        "success": True,
        "message": f"{category.capitalize()} permissions retrieved successfully",
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

@router.get("/resource/{resource}", dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_permissions_by_resource(
    resource: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """Get permissions by resource with pagination (SuperAdmin only)"""
    service = PermissionService()

    items, total, total_pages = service.get_paginated_permissions(
        page=page,
        page_size=page_size,
        resource=resource
    )

    return {
        "success": True,
        "message": f"Permissions for resource '{resource}' retrieved successfully",
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

@router.get("/search/query", dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def search_permissions(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """
    Search permissions by name or description (SuperAdmin only)

    Searches in permission name and description fields.
    """
    service = PermissionService()

    items, total, total_pages = service.get_paginated_permissions(
        page=page,
        page_size=page_size,
        search_query=q
    )

    return {
        "success": True,
        "message": "Search results retrieved successfully",
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

# ==================== Metadata Operations ====================

@router.get("/metadata/categories", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_categories():
    """Get all distinct permission categories (SuperAdmin only)"""
    service = PermissionService()

    categories = service.get_categories()

    return {
        "success": True,
        "message": "Categories retrieved successfully",
        "data": categories
    }

@router.get("/metadata/resources", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_resources():
    """Get all distinct resources (SuperAdmin only)"""
    service = PermissionService()

    resources = service.get_resources()

    return {
        "success": True,
        "message": "Resources retrieved successfully",
        "data": resources
    }

@router.get("/metadata/actions", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_actions():
    """Get all distinct actions (SuperAdmin only)"""
    service = PermissionService()

    actions = service.get_actions()

    return {
        "success": True,
        "message": "Actions retrieved successfully",
        "data": actions
    }

# ==================== Legacy/Compatibility Endpoints ====================

@router.get("/available/all", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_available_permissions():
    """Get all available permissions (SuperAdmin only) - Legacy endpoint"""
    service = PermissionService()

    permissions = service.get_all_available_permissions()

    return {
        "success": True,
        "message": "Available permissions retrieved successfully",
        "data": permissions
    }

@router.get("/categories/list", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_permission_categories():
    """Get permission categories (SuperAdmin only) - Legacy endpoint"""
    service = PermissionService()

    categories = service.get_permission_categories()

    return {
        "success": True,
        "message": "Permission categories retrieved successfully",
        "data": categories
    }

@router.get("/system/all", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_system_permissions():
    """Get all system permissions (SuperAdmin only) - Legacy endpoint"""
    service = PermissionService()

    permissions = service.get_permissions_by_category("system")

    return {
        "success": True,
        "message": "System permissions retrieved successfully",
        "data": permissions
    }

@router.get("/application/all", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_application_permissions():
    """Get all application permissions (SuperAdmin only) - Legacy endpoint"""
    service = PermissionService()

    permissions = service.get_permissions_by_category("application")

    return {
        "success": True,
        "message": "Application permissions retrieved successfully",
        "data": permissions
    }

@router.post("/validate/list", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def validate_permissions(permissions: List[str]):
    """Validate if permissions are valid (SuperAdmin only)"""
    service = PermissionService()

    validation_result = service.validate_permissions(permissions)

    return {
        "success": True,
        "message": "Permissions validated",
        "data": validation_result
    }

@router.get("/templates/all", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_permission_templates():
    """Get permission templates for predefined roles (SuperAdmin only)"""
    service = PermissionService()

    templates = service.get_permission_templates()

    return {
        "success": True,
        "message": "Permission templates retrieved successfully",
        "data": templates
    }

# ==================== Single-Resource Operations (must be LAST) ====================

@router.get("/{permission_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_permission(permission_id: str):
    """Get permission details by ID (SuperAdmin only)"""
    service = PermissionService()

    permission = service.get_permission_by_id(permission_id)

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    return {
        "success": True,
        "message": "Permission retrieved successfully",
        "data": permission
    }

@router.put("/{permission_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def update_permission(permission_id: str, permission: PermissionUpdate):
    """Update permission (SuperAdmin only)"""
    service = PermissionService()

    existing_permission = service.get_permission_by_id(permission_id)
    if not existing_permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    if permission.name and permission.name != existing_permission.get('name'):
        if service.permission_exists(permission.name, exclude_id=permission_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Permission '{permission.name}' already exists"
            )

    success = service.update_permission(permission_id, permission.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    return {
        "success": True,
        "message": "Permission updated successfully"
    }

@router.delete("/{permission_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def delete_permission(permission_id: str):
    """Soft delete permission (SuperAdmin only)"""
    service = PermissionService()

    permission = service.get_permission_by_id(permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    success = service.soft_delete_permission(permission_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    return {
        "success": True,
        "message": "Permission soft deleted successfully"
    }

@router.put("/{permission_id}/restore", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def restore_permission(permission_id: str):
    """Restore a soft-deleted permission (SuperAdmin only)"""
    service = PermissionService()

    permission = service.get_permission_by_id(permission_id, include_deleted=True)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    if not permission.get('is_deleted', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission is not deleted"
        )

    success = service.restore_permission(permission_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    return {
        "success": True,
        "message": "Permission restored successfully"
    }