"""
Permissions router — read-only access to application permissions.
Permissions are managed by the system service — this router exposes them
for the application UI (role assignment, display, filtering).
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Permission import PermissionService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/permissions", tags=["Permissions"])


# ---------------------------------------------------------------------------
# GET /permissions
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_permissions(
    category: Optional[str] = Query(None, max_length=50),
    resource: Optional[str] = Query(None, max_length=100),
    action: Optional[str] = Query(None, max_length=50),
    search: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated permissions with optional filters by category, resource, action, or search."""
    user_id = current_user.get("id")
    logger.info(
        "permissions.list.request user_id=%s category=%s resource=%s action=%s "
        "search=%r page=%s page_size=%s",
        user_id, category, resource, action, search, page, page_size,
    )

    items, total, total_pages = await PermissionService(db).get_paginated(
        page=page,
        page_size=page_size,
        category=category,
        resource=resource,
        action=action,
        search=search,
    )

    logger.info(
        "permissions.list.response user_id=%s total=%s page=%s total_pages=%s returned=%s",
        user_id, total, page, total_pages, len(items),
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


# ---------------------------------------------------------------------------
# GET /permissions/meta
# ---------------------------------------------------------------------------

@router.get("/meta", response_model=BaseResponse)
async def get_permissions_meta(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Return distinct resources and actions for UI filter dropdowns.
    Both queries run in parallel.
    """
    import asyncio

    user_id = current_user.get("id")
    logger.info("permissions.meta.request user_id=%s", user_id)

    service = PermissionService(db)
    resources, actions = await asyncio.gather(
        service.get_resources(),
        service.get_actions(),
    )

    logger.info(
        "permissions.meta.response user_id=%s resources=%s actions=%s",
        user_id, len(resources), len(actions),
    )
    return {
        "success": True,
        "message": "Permission metadata retrieved successfully",
        "data": {"resources": resources, "actions": actions},
    }


# ---------------------------------------------------------------------------
# GET /permissions/{permission_id}
# ---------------------------------------------------------------------------

@router.get("/{permission_id}", response_model=BaseResponse)
async def get_permission(
    permission_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a single permission by ID."""
    user_id = current_user.get("id")
    logger.info(
        "permissions.get.request user_id=%s permission_id=%s",
        user_id, permission_id,
    )

    permission = await PermissionService(db).get_by_id(permission_id)

    logger.info(
        "permissions.get.response user_id=%s permission_id=%s resource=%s action=%s",
        user_id, permission_id, permission.get("resource"), permission.get("action"),
    )
    return {"success": True, "message": "Permission retrieved successfully", "data": permission}
