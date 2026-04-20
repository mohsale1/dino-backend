from fastapi import APIRouter, HTTPException, status, Depends, Query, UploadFile, File
from src.schemas.Item import ItemCreate, ItemUpdate, ItemResponse
from src.application.services.Item import ItemService
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.config.Database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
import base64
import uuid

router = APIRouter(prefix="/items", tags=["Application Items"])


# ==================== BULK REQUEST MODELS ====================

class BulkUpdateAvailabilityRequest(BaseModel):
    item_ids: List[int]
    is_available: bool


class BulkDeleteRequest(BaseModel):
    item_ids: List[int]


class BulkUpdateCategoryRequest(BaseModel):
    item_ids: List[int]
    category_id: int


# ==================== COLLECTION ENDPOINTS ====================

@router.post("", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('items:create'))])
async def create_item(
    item: ItemCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new item (Admin only)"""
    service = ItemService(db)

    item_id = await service.create_item(item.model_dump())

    return {
        "success": True,
        "message": "Item created successfully",
        "data": {"id": item_id}
    }

@router.get("", dependencies=[Depends(ApplicationPermissionCheck.require('items:read'))])
async def get_all_items(
    workspace_id: int = Query(..., description="Workspace ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    is_available: Optional[bool] = Query(None, description="Filter by availability"),
    is_vegetarian: Optional[bool] = Query(None, description="Filter by veg/non-veg (True=Veg, False=Non-Veg)"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Order direction (asc/desc)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all items with pagination and filters

    Query Parameters:
    - workspace_id: Workspace ID (required)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - category_id: Filter by category
    - is_available: Filter by availability
    - is_vegetarian: Filter by veg/non-veg (True=Veg, False=Non-Veg, None=All)
    - search: Search query for name/description
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    """
    service = ItemService(db)

    if page_size > 100:
        page_size = 100

    items, total, total_pages = await service.get_paginated_items(
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
        category_id=category_id,
        is_available=is_available,
        is_vegetarian=is_vegetarian,
        search_query=search,
        order_by=order_by,
        order_direction=order_direction
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
            "has_prev": page > 1
        }
    }


# ==================== BULK ENDPOINTS (must be BEFORE /{item_id}) ====================

@router.post("/bulk-update-availability", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('items:update'))])
async def bulk_update_item_availability(
    body: BulkUpdateAvailabilityRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update item availability (Admin, Manager)"""
    service = ItemService(db)

    updated_count = 0
    failed_items = []

    for item_id in body.item_ids:
        try:
            item = await service.get_item_by_id(item_id)
            if not item:
                failed_items.append({"id": item_id, "reason": "Item not found"})
                continue

            success = await service.update_item(item_id, {"is_available": body.is_available})
            if success:
                updated_count += 1
            else:
                failed_items.append({"id": item_id, "reason": "Update failed"})
        except Exception as e:
            failed_items.append({"id": item_id, "reason": str(e)})

    return {
        "success": True,
        "message": f"Updated {updated_count} items",
        "data": {
            "updated_count": updated_count,
            "failed_items": failed_items
        }
    }

@router.post("/bulk-delete", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('items:delete'))])
async def bulk_delete_items(
    body: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk soft delete items (Admin only)"""
    service = ItemService(db)

    deleted_count = 0
    failed_items = []

    for item_id in body.item_ids:
        try:
            item = await service.get_item_by_id(item_id)
            if not item:
                failed_items.append({"id": item_id, "reason": "Item not found"})
                continue

            success = await service.soft_delete_item(item_id)
            if success:
                deleted_count += 1
            else:
                failed_items.append({"id": item_id, "reason": "Delete failed"})
        except Exception as e:
            failed_items.append({"id": item_id, "reason": str(e)})

    return {
        "success": True,
        "message": f"Deleted {deleted_count} items",
        "data": {
            "deleted_count": deleted_count,
            "failed_items": failed_items
        }
    }

@router.post("/bulk-update-category", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('items:update'))])
async def bulk_update_item_category(
    body: BulkUpdateCategoryRequest,
    db: AsyncSession = Depends(get_db)
):
    """Bulk update item category (Admin only)"""
    service = ItemService(db)

    updated_count = 0
    failed_items = []

    for item_id in body.item_ids:
        try:
            item = await service.get_item_by_id(item_id)
            if not item:
                failed_items.append({"id": item_id, "reason": "Item not found"})
                continue

            success = await service.update_item(item_id, {"category_id": body.category_id})
            if success:
                updated_count += 1
            else:
                failed_items.append({"id": item_id, "reason": "Update failed"})
        except Exception as e:
            failed_items.append({"id": item_id, "reason": str(e)})

    return {
        "success": True,
        "message": f"Updated {updated_count} items to new category",
        "data": {
            "updated_count": updated_count,
            "failed_items": failed_items
        }
    }


# ==================== ITEM-SCOPED ENDPOINTS (/{item_id}) ====================

@router.get("/{item_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('items:read'))])
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get item by ID"""
    service = ItemService(db)

    item = await service.get_item_by_id(item_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    return {
        "success": True,
        "message": "Item retrieved successfully",
        "data": item
    }

@router.put("/{item_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('items:update'))])
async def update_item(
    item_id: int,
    item: ItemUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update item (Admin only)"""
    service = ItemService(db)

    existing_item = await service.get_item_by_id(item_id)
    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    success = await service.update_item(item_id, item.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    return {
        "success": True,
        "message": "Item updated successfully"
    }

@router.delete("/{item_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('items:delete'))])
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete item (Admin only)"""
    service = ItemService(db)

    item = await service.get_item_by_id(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    success = await service.soft_delete_item(item_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    return {
        "success": True,
        "message": "Item soft deleted successfully"
    }

@router.put("/{item_id}/restore", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('items:restore'))])
async def restore_item(
    item_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Restore soft-deleted item (Admin only)"""
    service = ItemService(db)

    item = await service.get_item_by_id(item_id, include_deleted=True)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    if item.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item is not deleted"
        )

    success = await service.restore_item(item_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    return {
        "success": True,
        "message": "Item restored successfully"
    }

@router.put("/{item_id}/availability", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('items:update'))])
async def toggle_item_availability(
    item_id: int,
    is_available: bool = Query(..., description="Availability status"),
    db: AsyncSession = Depends(get_db)
):
    """Toggle item availability (Admin, Manager)"""
    service = ItemService(db)

    item = await service.get_item_by_id(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    success = await service.update_item(item_id, {"is_available": is_available})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    return {
        "success": True,
        "message": f"Item {'enabled' if is_available else 'disabled'} successfully"
    }


@router.post("/{item_id}/image", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('items:update'))])
async def upload_item_image(
    item_id: int,
    image: UploadFile = File(..., description="Item image file (JPEG, PNG, WebP, max 5MB)"),
    db: AsyncSession = Depends(get_db)
):
    """Upload or replace item image (Admin only). Stores image as base64 data URL."""
    service = ItemService(db)

    # Verify item exists
    item = await service.get_item_by_id(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    # Validate content type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    content_type = image.content_type or ""
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type '{content_type}'. Allowed: JPEG, PNG, WebP, GIF"
        )

    # Read and validate file size (5 MB limit)
    MAX_SIZE = 5 * 1024 * 1024
    contents = await image.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image file exceeds the 5 MB size limit"
        )

    # Encode as base64 data URL for storage
    b64 = base64.b64encode(contents).decode("utf-8")
    image_url = f"data:{content_type};base64,{b64}"

    success = await service.update_item(item_id, {"image_url": image_url})
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image"
        )

    return {
        "success": True,
        "message": "Item image uploaded successfully",
        "data": {"image_url": image_url}
    }
