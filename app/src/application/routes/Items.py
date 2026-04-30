"""
Items router — CRUD for menu items.
"""

from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Item import ItemService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/items", tags=["Items"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_workspace(current_user: Dict[str, Any]) -> int:
    wid = current_user.get("workspace_id")
    if not wid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id required",
        )
    return wid


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateItemRequest(BaseModel):
    persona_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    is_available: bool = True
    is_vegetarian: Optional[bool] = None
    category_id: int = Field(..., ge=1)


class UpdateItemRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    is_available: Optional[bool] = None
    is_vegetarian: Optional[bool] = None
    category_id: Optional[int] = Field(None, ge=1)


class UpdateAvailabilityRequest(BaseModel):
    is_available: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_items(
    persona_id: int = Query(..., ge=1),
    category_id: Optional[int] = Query(None),
    is_available: Optional[bool] = Query(None),
    is_vegetarian: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated items scoped to a persona."""
    wid = _require_workspace(current_user)
    service = ItemService(db)
    items, total, total_pages = await service.get_paginated_items(
        workspace_id=wid,
        persona_id=persona_id,
        category_id=category_id,
        is_available=is_available,
        is_vegetarian=is_vegetarian,
        search=search,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "message": "Items retrieved successfully",
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
async def create_item(
    request: CreateItemRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new menu item."""
    wid = _require_workspace(current_user)
    service = ItemService(db)
    data = request.model_dump(exclude_none=True)
    data["workspace_id"] = wid
    item = await service.create_item(data)
    return {"success": True, "message": "Item created successfully", "data": item}


@router.get("/{item_id}", response_model=BaseResponse)
async def get_item(
    item_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a menu item by ID scoped to persona."""
    wid = _require_workspace(current_user)
    service = ItemService(db)
    item = await service.get_item_for_persona(item_id, wid, persona_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return {"success": True, "message": "Item retrieved successfully", "data": item}


@router.put("/{item_id}", response_model=BaseResponse)
async def update_item(
    item_id: int,
    request: UpdateItemRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a menu item."""
    wid = _require_workspace(current_user)
    data = request.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    service = ItemService(db)
    updated = await service.update_item(item_id, wid, persona_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return {"success": True, "message": "Item updated successfully"}


@router.put("/{item_id}/availability", response_model=BaseResponse)
async def update_item_availability(
    item_id: int,
    request: UpdateAvailabilityRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:update")),
    db: AsyncSession = Depends(get_db),
):
    """Toggle item availability."""
    wid = _require_workspace(current_user)
    service = ItemService(db)
    updated = await service.update_availability(item_id, wid, persona_id, request.is_available)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return {"success": True, "message": "Item availability updated successfully"}


@router.delete("/{item_id}", response_model=BaseResponse)
async def delete_item(
    item_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a menu item."""
    wid = _require_workspace(current_user)
    service = ItemService(db)
    deleted = await service.soft_delete_item(item_id, wid, persona_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return {"success": True, "message": "Item deleted successfully"}


@router.post("/{item_id}/restore", response_model=BaseResponse)
async def restore_item(
    item_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:update")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted menu item."""
    wid = _require_workspace(current_user)
    service = ItemService(db)
    restored = await service.restore_item(item_id, wid, persona_id)
    if not restored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found or is not deleted",
        )
    return {"success": True, "message": "Item restored successfully"}
