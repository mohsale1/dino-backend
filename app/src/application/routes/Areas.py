"""
Areas router — CRUD for dining areas, scoped by persona_id.
"""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Area import AreaService
from src.schemas.Area import AreaCreate, AreaUpdate
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/areas", tags=["Areas"])


@router.get("", response_model=BaseResponse)
async def get_areas(
    persona_id: int = Query(..., ge=1),
    is_available: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:read")),
    db: AsyncSession = Depends(get_db),
):
    """List paginated areas scoped to persona."""
    try:
        items, total, total_pages = await AreaService(db).get_all_areas(
            persona_id=persona_id, is_available=is_available, page=page, page_size=page_size
        )
        return {
            "success": True,
            "message": "Areas retrieved successfully",
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
    except Exception as e:
        logger.exception("areas.list.failed persona_id=%s error=%s", persona_id, str(e))
        return {"success": False, "message": "Failed to retrieve areas", "error_code": "INTERNAL_ERROR"}


@router.post("", response_model=BaseResponse, status_code=201)
async def create_area(
    request: AreaCreate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new area scoped to persona."""
    try:
        area = await AreaService(db).create_area(request.model_dump())
        return {"success": True, "message": "Area created successfully", "data": area}
    except PermissionDeniedError:
        return {"success": False, "message": "You do not have permission to create areas", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        logger.exception("areas.create.failed error=%s", str(e))
        return {"success": False, "message": "Failed to create area", "error_code": "INTERNAL_ERROR"}


@router.get("/{area_id}", response_model=BaseResponse)
async def get_area(
    area_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single area scoped to persona."""
    try:
        area = await AreaService(db).get_area_for_persona(area_id, persona_id)
        if not area:
            raise NotFoundError("Area not found")
        return {"success": True, "message": "Area retrieved successfully", "data": area}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("areas.get.failed error=%s", str(e))
        return {"success": False, "message": "Failed to retrieve area", "error_code": "INTERNAL_ERROR"}


@router.put("/{area_id}", response_model=BaseResponse)
async def update_area(
    area_id: int,
    request: AreaUpdate,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an area."""
    try:
        data = request.model_dump(exclude_unset=True)
        if not data:
            raise BadRequestError("No fields provided for update")

        updated = await AreaService(db).update_area(area_id, persona_id, data)
        if not updated:
            raise NotFoundError("Area not found")
        return {"success": True, "message": "Area updated successfully"}
    except BadRequestError as e:
        return {"success": False, "message": str(e), "error_code": "BAD_REQUEST"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("areas.update.failed error=%s", str(e))
        return {"success": False, "message": "Failed to update area", "error_code": "INTERNAL_ERROR"}


@router.delete("/{area_id}", response_model=BaseResponse)
async def delete_area(
    area_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an area."""
    try:
        deleted = await AreaService(db).soft_delete_area(area_id, persona_id)
        if not deleted:
            raise NotFoundError("Area not found")
        return {"success": True, "message": "Area deleted successfully"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("areas.delete.failed error=%s", str(e))
        return {"success": False, "message": "Failed to delete area", "error_code": "INTERNAL_ERROR"}


@router.post("/{area_id}/restore", response_model=BaseResponse)
async def restore_area(
    area_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:restore")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted area. Requires 'areas:restore' permission."""
    try:
        restored = await AreaService(db).restore_area(area_id, persona_id)
        if not restored:
            raise NotFoundError("Area not found or is not deleted")
        return {"success": True, "message": "Area restored successfully"}
    except PermissionDeniedError:
        return {"success": False, "message": "You do not have permission to restore areas", "error_code": "PERMISSION_DENIED"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("areas.restore.failed error=%s", str(e))
        return {"success": False, "message": "Failed to restore area", "error_code": "INTERNAL_ERROR"}