from fastapi import APIRouter, Body, HTTPException, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.base.BaseSchema import BaseResponse
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.Permission import PermissionService
from src.schemas.Permission import (
    PermissionCreate,
    PermissionUpdate,
    PermissionResponse,
    PermissionBulkCreate
)
from src.config.Database import get_db
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/permissions", tags=["System Permissions"])

# ==================== CRUD Collection Operations ====================

@router.post("", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:create'))])
async def create_permission(permission: PermissionCreate, db: AsyncSession = Depends(get_db)):
    """
    Create new permission

    Creates a new permission in the system.
    """
    service = PermissionService(db)

    if await service.permission_exists(permission.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Permission '{permission.name}' already exists"
        )

    permission_id = await service.create_permission(permission.model_dump())

    return {
        "success": True,
        "message": "Permission created successfully",
        "data": {"id": permission_id}
    }

@router.get("", dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def get_all_permissions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category (system/application)"),
    resource: Optional[str] = Query(None, description="Filter by resource"),
    action: Optional[str] = Query(None, description="Filter by action"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Order direction (asc/desc)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all permissions with pagination and filtering

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
    service = PermissionService(db)

    if category and category not in ['system', 'application']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="category must be 'system' or 'application'"
        )

    if page_size > 100:
        page_size = 100

    items, total, total_pages = await service.get_paginated_permissions(
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

@router.post("/bulk", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:create'))])
async def bulk_create_permissions(bulk_data: PermissionBulkCreate, db: AsyncSession = Depends(get_db)):
    """
    Bulk create permissions

    Creates multiple permissions at once.
    """
    service = PermissionService(db)

    names = [p.name for p in bulk_data.permissions]
    if len(names) != len(set(names)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate permission names in request"
        )

    existing = []
    for perm in bulk_data.permissions:
        if await service.permission_exists(perm.name):
            existing.append(perm.name)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Permissions already exist: {', '.join(existing)}"
        )

    permissions_data = [p.model_dump() for p in bulk_data.permissions]
    permission_ids = await service.bulk_create_permissions(permissions_data)

    return {
        "success": True,
        "message": f"{len(permission_ids)} permissions created successfully",
        "data": {
            "ids": permission_ids,
            "count": len(permission_ids)
        }
    }

# ==================== Query Operations ====================

@router.get("/category/{category}", dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def get_permissions_by_category(
    category: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get permissions by category with pagination

    Categories: system, application
    """
    service = PermissionService(db)

    if category not in ['system', 'application']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="category must be 'system' or 'application'"
        )

    items, total, total_pages = await service.get_paginated_permissions(
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

@router.get("/resource/{resource}", dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def get_permissions_by_resource(
    resource: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get permissions by resource with pagination"""
    service = PermissionService(db)

    items, total, total_pages = await service.get_paginated_permissions(
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

@router.get("/search/query", dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def search_permissions(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Search permissions by name or description

    Searches in permission name and description fields.
    """
    service = PermissionService(db)

    items, total, total_pages = await service.get_paginated_permissions(
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

@router.get("/metadata/categories", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all distinct permission categories"""
    service = PermissionService(db)

    categories = await service.get_categories()

    return {
        "success": True,
        "message": "Categories retrieved successfully",
        "data": categories
    }

@router.get("/metadata/resources", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def get_resources(db: AsyncSession = Depends(get_db)):
    """Get all distinct resources"""
    service = PermissionService(db)

    resources = await service.get_resources()

    return {
        "success": True,
        "message": "Resources retrieved successfully",
        "data": resources
    }

@router.get("/metadata/actions", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def get_actions(db: AsyncSession = Depends(get_db)):
    """Get all distinct actions"""
    service = PermissionService(db)

    actions = await service.get_actions()

    return {
        "success": True,
        "message": "Actions retrieved successfully",
        "data": actions
    }

# ==================== Legacy/Compatibility Endpoints ====================

@router.get("/available/all", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def get_available_permissions(db: AsyncSession = Depends(get_db)):
    """Get all available permissions - Legacy endpoint"""
    service = PermissionService(db)

    # sync — no DB access
    permissions = service.get_all_available_permissions()

    return {
        "success": True,
        "message": "Available permissions retrieved successfully",
        "data": permissions
    }

@router.get("/categories/list", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def get_permission_categories(db: AsyncSession = Depends(get_db)):
    """Get permission categories - Legacy endpoint"""
    service = PermissionService(db)

    # sync — no DB access
    categories = service.get_permission_categories()

    return {
        "success": True,
        "message": "Permission categories retrieved successfully",
        "data": categories
    }

@router.get("/system/all", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def get_system_permissions(db: AsyncSession = Depends(get_db)):
    """Get all system permissions - Legacy endpoint"""
    service = PermissionService(db)

    permissions = await service.get_permissions_by_category("system")

    return {
        "success": True,
        "message": "System permissions retrieved successfully",
        "data": permissions
    }

@router.get("/application/all", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def get_application_permissions(db: AsyncSession = Depends(get_db)):
    """Get all application permissions - Legacy endpoint"""
    service = PermissionService(db)

    permissions = await service.get_permissions_by_category("application")

    return {
        "success": True,
        "message": "Application permissions retrieved successfully",
        "data": permissions
    }

@router.post("/validate/list", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def validate_permissions(permissions: List[str] = Body(...), db: AsyncSession = Depends(get_db)):
    """Validate if permissions are valid"""
    service = PermissionService(db)

    # sync — operates on in-memory definitions only
    validation_result = service.validate_permissions(permissions)

    return {
        "success": True,
        "message": "Permissions validated",
        "data": validation_result
    }

@router.get("/templates/all", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def get_permission_templates(db: AsyncSession = Depends(get_db)):
    """Get permission templates for predefined roles"""
    service = PermissionService(db)

    # sync — operates on in-memory definitions only
    templates = service.get_permission_templates()

    return {
        "success": True,
        "message": "Permission templates retrieved successfully",
        "data": templates
    }

# ==================== Single-Resource Operations (must be LAST) ====================

@router.get("/{permission_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:read'))])
async def get_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    """Get permission details by ID"""
    service = PermissionService(db)

    permission = await service.get_permission_by_id(permission_id)

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

@router.put("/{permission_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:update'))])
async def update_permission(permission_id: int, permission: PermissionUpdate, db: AsyncSession = Depends(get_db)):
    """Update permission"""
    service = PermissionService(db)

    existing_permission = await service.get_permission_by_id(permission_id)
    if not existing_permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    if permission.name and permission.name != existing_permission.get('name'):
        if await service.permission_exists(permission.name, exclude_id=permission_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Permission '{permission.name}' already exists"
            )

    success = await service.update_permission(permission_id, permission.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    return {
        "success": True,
        "message": "Permission updated successfully"
    }

@router.delete("/{permission_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:delete'))])
async def delete_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete permission"""
    service = PermissionService(db)

    permission = await service.get_permission_by_id(permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    success = await service.soft_delete_permission(permission_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    return {
        "success": True,
        "message": "Permission soft deleted successfully"
    }

@router.put("/{permission_id}/restore", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('permissions:restore'))])
async def restore_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    """Restore a soft-deleted permission"""
    service = PermissionService(db)

    permission = await service.get_permission_by_id(permission_id, include_deleted=True)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    if permission.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission is not deleted"
        )

    success = await service.restore_permission(permission_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    return {
        "success": True,
        "message": "Permission restored successfully"
    }
