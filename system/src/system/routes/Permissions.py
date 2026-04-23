from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.schemas.Permission import PermissionBulkCreate, PermissionCreate, PermissionUpdate
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.Permission import PermissionService

router = APIRouter(prefix="/permissions", tags=["System Permissions"])


@router.get(
    "",
     dependencies=[Depends(SystemPermissionCheck.require("permissions:read"))],
)
async def get_permissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    resource: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated permissions with filters."""
    service = PermissionService(db)
    items, total, total_pages = await service.get_paginated_permissions(
        category=category,
        resource=resource,
        action=action,
        is_active=is_active,
        page=page,
        page_size=page_size,
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
            "has_prev": page > 1,
        },
    }


@router.post(
    "",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("permissions:create"))],
)
async def create_permission(permission: PermissionCreate, db: AsyncSession = Depends(get_db)):
    """Create a new permission."""
    service = PermissionService(db)
    try:
        created = await service.create_permission(permission.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return {
        "success": True,
        "message": "Permission created successfully",
        "data": {"id": created.get("id")},
    }


@router.post(
    "/bulk",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("permissions:create"))],
)
async def bulk_create_permissions(
    bulk_data: PermissionBulkCreate, db: AsyncSession = Depends(get_db)
):
    """Bulk create permissions (skips duplicates)."""
    service = PermissionService(db)
    permissions_data = [p.model_dump() for p in bulk_data.permissions]
    created = await service.bulk_create_permissions(permissions_data)
    return {
        "success": True,
        "message": f"{len(created)} permissions created successfully",
        "data": {"count": len(created)},
    }


@router.get(
    "/meta/categories",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("permissions:read"))],
)
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get distinct permission categories."""
    service = PermissionService(db)
    categories = await service.get_categories()
    return {"success": True, "message": "Categories retrieved successfully", "data": categories}


@router.get(
    "/meta/resources",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("permissions:read"))],
)
async def get_resources(db: AsyncSession = Depends(get_db)):
    """Get distinct permission resources."""
    service = PermissionService(db)
    resources = await service.get_resources()
    return {"success": True, "message": "Resources retrieved successfully", "data": resources}


@router.get(
    "/{permission_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("permissions:read"))],
)
async def get_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    """Get permission details."""
    service = PermissionService(db)
    permission = await service.get_permission_by_id(permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return {"success": True, "message": "Permission retrieved successfully", "data": permission}


@router.put(
    "/{permission_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("permissions:update"))],
)
async def update_permission(
    permission_id: int, permission: PermissionUpdate, db: AsyncSession = Depends(get_db)
):
    """Update permission."""
    service = PermissionService(db)
    existing = await service.get_permission_by_id(permission_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    data = permission.model_dump(exclude_unset=True)
    # Check uniqueness if category/resource/action changed
    if any(k in data for k in ("category", "resource", "action")):
        check_cat = data.get("category", existing.get("category"))
        check_res = data.get("resource", existing.get("resource"))
        check_act = data.get("action", existing.get("action"))
        if await service.permission_exists(check_cat, check_res, check_act, exclude_id=permission_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A permission with this category/resource/action already exists",
            )

    success = await service.update_permission(permission_id, data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return {"success": True, "message": "Permission updated successfully"}


@router.delete(
    "/{permission_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("permissions:delete"))],
)
async def delete_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete permission."""
    service = PermissionService(db)
    permission = await service.get_permission_by_id(permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    success = await service.soft_delete_permission(permission_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return {"success": True, "message": "Permission deleted successfully"}


@router.post(
    "/{permission_id}/restore",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("permissions:update"))],
)
async def restore_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    """Restore a soft-deleted permission."""
    service = PermissionService(db)
    permission = await service.get_permission_by_id(permission_id, include_deleted=True)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    if permission.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission is not deleted",
        )
    success = await service.restore_permission(permission_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return {"success": True, "message": "Permission restored successfully"}