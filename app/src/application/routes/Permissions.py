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
from src.core.Exceptions import NotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get("", response_model=BaseResponse)
async def get_permissions(
    category: Optional[str] = Query(None, max_length=50),
    resource: Optional[str] = Query(None, max_length=100),
    action: Optional[str] = Query(None, max_length=50),
    search: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("permissions:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated permissions with optional filters by category, resource, action, or search."""
    try:
        items, total, total_pages = await PermissionService(db).get_paginated(
            page=page,
            page_size=page_size,
            category=category,
            resource=resource,
            action=action,
            search=search,
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
    except PermissionDeniedError:
        return {"success": False, "message": "You do not have permission to view permissions", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        logger.exception("permissions.list.failed error=%s", str(e))
        return {"success": False, "message": "Failed to retrieve permissions", "error_code": "INTERNAL_ERROR"}


@router.get("/meta", response_model=BaseResponse)
async def get_permissions_meta(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("permissions:read")),
    db: AsyncSession = Depends(get_db),
):
    """Return distinct resources and actions for UI filter dropdowns."""
    import asyncio
    try:
        service = PermissionService(db)
        resources, actions = await asyncio.gather(
            service.get_resources(),
            service.get_actions(),
        )
        return {
            "success": True,
            "message": "Permission metadata retrieved successfully",
            "data": {"resources": resources, "actions": actions},
        }
    except PermissionDeniedError:
        return {"success": False, "message": "You do not have permission to view permission metadata", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        logger.exception("permissions.meta.failed error=%s", str(e))
        return {"success": False, "message": "Failed to retrieve permission metadata", "error_code": "INTERNAL_ERROR"}


@router.get("/{permission_id}", response_model=BaseResponse)
async def get_permission(
    permission_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("permissions:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single permission by ID."""
    try:
        permission = await PermissionService(db).get_by_id(permission_id)
        if not permission:
            raise NotFoundError("Permission not found")
        return {"success": True, "message": "Permission retrieved successfully", "data": permission}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except PermissionDeniedError:
        return {"success": False, "message": "You do not have permission to view this permission", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        logger.exception("permissions.get.failed error=%s", str(e))
        return {"success": False, "message": "Failed to retrieve permission", "error_code": "INTERNAL_ERROR"}
