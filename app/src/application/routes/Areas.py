"""
Areas router — CRUD for dining areas.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Area import AreaService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/areas", tags=["Areas"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateAreaRequest(BaseModel):
    name: str
    description: Optional[str] = None
    workspace_id: Optional[int] = None
    persona_id: Optional[int] = None
    is_available: bool = True


class UpdateAreaRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    persona_id: Optional[int] = None
    is_available: Optional[bool] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_areas(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    is_available: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated areas."""
    wid = workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = AreaService(db)
    items, total, total_pages = await service.get_paginated_areas(
        workspace_id=wid,
        persona_id=persona_id,
        is_available=is_available,
        page=page,
        page_size=page_size,
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


@router.post("", response_model=BaseResponse)
async def create_area(
    request: CreateAreaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new area."""
    wid = request.workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = AreaService(db)
    data = request.model_dump()
    data["workspace_id"] = wid
    area = await service.create_area(data)
    return {"success": True, "message": "Area created successfully", "data": area}


@router.get("/{area_id}", response_model=BaseResponse)
async def get_area(
    area_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get an area by ID."""
    service = AreaService(db)
    area = await service.get_by_id(area_id)
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return {"success": True, "message": "Area retrieved successfully", "data": area}


@router.put("/{area_id}", response_model=BaseResponse)
async def update_area(
    area_id: int,
    request: UpdateAreaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an area."""
    service = AreaService(db)
    existing = await service.get_by_id(area_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    data = request.model_dump(exclude_unset=True)
    success = await service.update_area(area_id, data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return {"success": True, "message": "Area updated successfully"}


@router.delete("/{area_id}", response_model=BaseResponse)
async def delete_area(
    area_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an area."""
    service = AreaService(db)
    existing = await service.get_by_id(area_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    success = await service.soft_delete_area(area_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return {"success": True, "message": "Area deleted successfully"}


@router.post("/{area_id}/restore", response_model=BaseResponse)
async def restore_area(
    area_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:restore")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted area."""
    service = AreaService(db)
    existing = await service.get_by_id(area_id, include_deleted=True)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    if existing.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Area is not deleted")
    success = await service.restore_area(area_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return {"success": True, "message": "Area restored successfully"}
