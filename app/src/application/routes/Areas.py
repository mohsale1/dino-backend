"""
Areas router — CRUD for dining areas, scoped by persona_id.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Area import AreaService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/areas", tags=["Areas"])


class CreateAreaRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    persona_id: int = Field(..., ge=1)
    is_available: bool = True


class UpdateAreaRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_available: Optional[bool] = None


@router.get("", response_model=BaseResponse)
async def get_areas(
    persona_id: int = Query(..., ge=1),
    is_available: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """List paginated areas scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "areas.list.request user_id=%s persona_id=%s is_available=%s page=%s page_size=%s",
        user_id, persona_id, is_available, page, page_size,
    )

    items, total, total_pages = await AreaService(db).get_all_areas(
        persona_id=persona_id,
        is_available=is_available,
        page=page,
        page_size=page_size,
    )

    logger.info(
        "areas.list.response user_id=%s persona_id=%s total=%s page=%s total_pages=%s returned=%s",
        user_id, persona_id, total, page, total_pages, len(items),
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


@router.post("", response_model=BaseResponse, status_code=201)
async def create_area(
    request: CreateAreaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Create a new area scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "areas.create.request user_id=%s persona_id=%s name=%r",
        user_id, request.persona_id, request.name,
    )

    data = request.model_dump()
    area = await AreaService(db).create_area(data)

    logger.info(
        "areas.create.response user_id=%s persona_id=%s area_id=%s name=%r",
        user_id, request.persona_id, area.get("id"), area.get("name"),
    )
    return {"success": True, "message": "Area created successfully", "data": area}


@router.get("/{area_id}", response_model=BaseResponse)
async def get_area(
    area_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a single area scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "areas.get.request user_id=%s area_id=%s persona_id=%s",
        user_id, area_id, persona_id,
    )

    area = await AreaService(db).get_area_for_persona(area_id, persona_id)
    if not area:
        logger.warning(
            "areas.get.not_found user_id=%s area_id=%s persona_id=%s",
            user_id, area_id, persona_id,
        )
        raise NotFoundError("Area not found")

    logger.info(
        "areas.get.response user_id=%s area_id=%s persona_id=%s name=%r",
        user_id, area_id, persona_id, area.get("name"),
    )
    return {"success": True, "message": "Area retrieved successfully", "data": area}


@router.put("/{area_id}", response_model=BaseResponse)
async def update_area(
    area_id: int,
    request: UpdateAreaRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update name, description, or is_available for an area."""
    user_id = current_user.get("id")
    data = request.model_dump(exclude_unset=True)

    if not data:
        logger.warning(
            "areas.update.empty_payload user_id=%s area_id=%s persona_id=%s",
            user_id, area_id, persona_id,
        )
        raise BadRequestError("No fields provided for update")

    logger.info(
        "areas.update.request user_id=%s area_id=%s persona_id=%s fields=%s",
        user_id, area_id, persona_id, list(data.keys()),
    )

    updated = await AreaService(db).update_area(area_id, persona_id, data)
    if not updated:
        logger.warning(
            "areas.update.not_found user_id=%s area_id=%s persona_id=%s",
            user_id, area_id, persona_id,
        )
        raise NotFoundError("Area not found")

    logger.info(
        "areas.update.response user_id=%s area_id=%s persona_id=%s fields=%s",
        user_id, area_id, persona_id, list(data.keys()),
    )
    return {"success": True, "message": "Area updated successfully"}


@router.delete("/{area_id}", response_model=BaseResponse)
async def delete_area(
    area_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an area."""
    user_id = current_user.get("id")
    logger.info(
        "areas.delete.request user_id=%s area_id=%s persona_id=%s",
        user_id, area_id, persona_id,
    )

    deleted = await AreaService(db).soft_delete_area(area_id, persona_id)
    if not deleted:
        logger.warning(
            "areas.delete.not_found user_id=%s area_id=%s persona_id=%s",
            user_id, area_id, persona_id,
        )
        raise NotFoundError("Area not found")

    logger.info(
        "areas.delete.response user_id=%s area_id=%s persona_id=%s",
        user_id, area_id, persona_id,
    )
    return {"success": True, "message": "Area deleted successfully"}



@router.post("/{area_id}/restore", response_model=BaseResponse)
async def restore_area(
    area_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted area."""
    user_id = current_user.get("id")
    logger.info(
        "areas.restore.request user_id=%s area_id=%s persona_id=%s",
        user_id, area_id, persona_id,
    )

    restored = await AreaService(db).restore_area(area_id, persona_id)
    if not restored:
        logger.warning(
            "areas.restore.not_found user_id=%s area_id=%s persona_id=%s",
            user_id, area_id, persona_id,
        )
        raise NotFoundError("Area not found or is not deleted")

    logger.info(
        "areas.restore.response user_id=%s area_id=%s persona_id=%s",
        user_id, area_id, persona_id,
    )
    return {"success": True, "message": "Area restored successfully"}
