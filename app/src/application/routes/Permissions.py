"""
Permissions router — read-only access to application permissions.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.repositories.PermissionRepository import PermissionRepository

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get("", response_model=BaseResponse)
async def get_permissions(
    resource: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("permissions:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get all permissions with optional filters."""
    repo = PermissionRepository(db)
    items, total, total_pages = await repo.get_paginated_with_filters(
        page=page,
        page_size=page_size,
        resource=resource,
        action=action,
        search_query=search,
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


@router.get("/{permission_id}", response_model=BaseResponse)
async def get_permission(
    permission_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("permissions:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a permission by ID."""
    repo = PermissionRepository(db)
    permission = await repo.get_by_id(permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
    return {"success": True, "message": "Permission retrieved successfully", "data": permission}
