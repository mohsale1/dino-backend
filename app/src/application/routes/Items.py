"""
Items router — CRUD for menu items.
"""

from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Item import ItemService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/items", tags=["Items"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateItemRequest(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    price: Decimal
    is_available: bool = True
    is_vegetarian: Optional[bool] = None
    workspace_id: Optional[int] = None
    category_id: int


class UpdateItemRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[Decimal] = None
    is_available: Optional[bool] = None
    is_vegetarian: Optional[bool] = None
    category_id: Optional[int] = None


class UpdateAvailabilityRequest(BaseModel):
    is_available: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_items(
    workspace_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    is_available: Optional[bool] = Query(None),
    is_vegetarian: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated items with optional filters."""
    wid = workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = ItemService(db)
    items, total, total_pages = await service.get_paginated_items(
        workspace_id=wid,
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


@router.post("", response_model=BaseResponse)
async def create_item(
    request: CreateItemRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new menu item."""
    wid = request.workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = ItemService(db)
    data = request.model_dump()
    data["workspace_id"] = wid
    item = await service.create_item(data)
    return {"success": True, "message": "Item created successfully", "data": item}


@router.get("/{item_id}", response_model=BaseResponse)
async def get_item(
    item_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a menu item by ID."""
    service = ItemService(db)
    item = await service.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return {"success": True, "message": "Item retrieved successfully", "data": item}


@router.put("/{item_id}", response_model=BaseResponse)
async def update_item(
    item_id: int,
    request: UpdateItemRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a menu item."""
    service = ItemService(db)
    existing = await service.get_by_id(item_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    data = request.model_dump(exclude_unset=True)
    success = await service.update_item(item_id, data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return {"success": True, "message": "Item updated successfully"}


@router.put("/{item_id}/availability", response_model=BaseResponse)
async def update_item_availability(
    item_id: int,
    request: UpdateAvailabilityRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:update")),
    db: AsyncSession = Depends(get_db),
):
    """Toggle item availability."""
    service = ItemService(db)
    existing = await service.get_by_id(item_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    success = await service.update_availability(item_id, request.is_available)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return {"success": True, "message": "Item availability updated successfully"}


@router.delete("/{item_id}", response_model=BaseResponse)
async def delete_item(
    item_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a menu item."""
    service = ItemService(db)
    existing = await service.get_by_id(item_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    success = await service.soft_delete_item(item_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return {"success": True, "message": "Item deleted successfully"}


@router.post("/{item_id}/restore", response_model=BaseResponse)
async def restore_item(
    item_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:manage")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted menu item."""
    service = ItemService(db)
    existing = await service.get_by_id(item_id, include_deleted=True)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if existing.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item is not deleted")
    success = await service.restore_item(item_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return {"success": True, "message": "Item restored successfully"}
