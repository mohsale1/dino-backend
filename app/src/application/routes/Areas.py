"""
Areas router â€” CRUD for dining areas, scoped by workspace (JWT) and persona.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
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
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    persona_id: int = Field(..., ge=1)
    is_available: bool = True


class UpdateAreaRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_available: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_workspace(current_user: Dict[str, Any]) -> int:
    """Extract workspace_id from JWT claims; raise 400 if absent."""
    wid = current_user.get("workspace_id")
    if not wid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id required",
        )
    return wid


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_areas(
    persona_id: int = Query(..., ge=1),
    is_available: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:read")),
    db: AsyncSession = Depends(get_db),
):
    """List paginated areas scoped to workspace + persona, ordered oldest-first with 1-based absolute index."""
    wid = _require_workspace(current_user)
    service = AreaService(db)
    items, total, total_pages = await service.get_all_areas(
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



@router.post("", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_area(
    request: CreateAreaRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:create")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new area scoped to workspace + persona.
    Automatically links the persona to the workspace in workspace_personas if not already linked.
    """
    wid = _require_workspace(current_user)
    service = AreaService(db)
    data = request.model_dump()
    data["workspace_id"] = wid
    area = await service.create_area(data)
    return {"success": True, "message": "Area created successfully", "data": area}


@router.get("/{area_id}", response_model=BaseResponse)
async def get_area(
    area_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single area scoped to workspace + persona."""
    wid = _require_workspace(current_user)
    service = AreaService(db)
    area = await service.get_area_for_persona(area_id, wid, persona_id)
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return {"success": True, "message": "Area retrieved successfully", "data": area}


@router.put("/{area_id}", response_model=BaseResponse)
async def update_area(
    area_id: int,
    request: UpdateAreaRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update name, description, or is_available for an area scoped to workspace + persona."""
    wid = _require_workspace(current_user)
    data = request.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    service = AreaService(db)
    updated = await service.update_area(area_id, wid, persona_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return {"success": True, "message": "Area updated successfully"}


@router.delete("/{area_id}", response_model=BaseResponse)
async def delete_area(
    area_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an area (sets is_active=False) scoped to workspace + persona."""
    wid = _require_workspace(current_user)
    service = AreaService(db)
    deleted = await service.soft_delete_area(
        area_id, wid, persona_id, updated_by=current_user.get("id")
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return {"success": True, "message": "Area deleted successfully"}


@router.post("/{area_id}/restore", response_model=BaseResponse)
async def restore_area(
    area_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("areas:update")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted area scoped to workspace + persona."""
    wid = _require_workspace(current_user)
    service = AreaService(db)
    restored = await service.restore_area(area_id, wid, persona_id)
    if not restored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found or is not deleted",
        )
    return {"success": True, "message": "Area restored successfully"}
