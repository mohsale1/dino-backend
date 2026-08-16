"""
Items router — CRUD for menu items, scoped by persona_id.
"""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Item import ItemService
from src.application.schemas.items import ItemCreate, ItemUpdate, ItemAvailabilityUpdate
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/items", tags=["Items"])


@router.get("", response_model=BaseResponse)
async def get_items(
    persona_id: int = Query(..., ge=1),
    category_id: Optional[int] = Query(None, ge=1),
    is_available: Optional[bool] = Query(None),
    is_vegetarian: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated items scoped to persona with optional filters."""
    try:
        items, total, total_pages = await ItemService(db).get_paginated_items(
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
    except Exception as e:
        logger.exception("items.list.failed persona_id=%s error=%s", persona_id, str(e))
        return {"success": False, "message": "Failed to retrieve items", "error_code": "INTERNAL_ERROR"}


@router.post("", response_model=BaseResponse, status_code=201)
async def create_item(
    request: ItemCreate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new menu item scoped to persona."""
    try:
        item = await ItemService(db).create_item(request.model_dump())
        return {"success": True, "message": "Item created successfully", "data": item}
    except PermissionDeniedError:
        return {"success": False, "message": "You do not have permission to create items", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        logger.exception("items.create.failed error=%s", str(e))
        return {"success": False, "message": "Failed to create item", "error_code": "INTERNAL_ERROR"}


@router.get("/{item_id}", response_model=BaseResponse)
async def get_item(
    item_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a menu item by ID scoped to persona."""
    try:
        item = await ItemService(db).get_item_for_persona(item_id, persona_id)
        if not item:
            raise NotFoundError("Item not found")
        return {"success": True, "message": "Item retrieved successfully", "data": item}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("items.get.failed error=%s", str(e))
        return {"success": False, "message": "Failed to retrieve item", "error_code": "INTERNAL_ERROR"}


@router.put("/{item_id}", response_model=BaseResponse)
async def update_item(
    item_id: int,
    request: ItemUpdate,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a menu item scoped to persona."""
    try:
        data = request.model_dump(exclude_unset=True)
        if not data:
            raise BadRequestError("No fields provided for update")

        updated = await ItemService(db).update_item(item_id, persona_id, data)
        if not updated:
            raise NotFoundError("Item not found")
        return {"success": True, "message": "Item updated successfully"}
    except BadRequestError as e:
        return {"success": False, "message": str(e), "error_code": "BAD_REQUEST"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("items.update.failed error=%s", str(e))
        return {"success": False, "message": "Failed to update item", "error_code": "INTERNAL_ERROR"}


@router.put("/{item_id}/availability", response_model=BaseResponse)
async def update_item_availability(
    item_id: int,
    request: ItemAvailabilityUpdate,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:update")),
    db: AsyncSession = Depends(get_db),
):
    """Toggle item availability scoped to persona."""
    try:
        updated = await ItemService(db).update_availability(item_id, persona_id, request.is_available)
        if not updated:
            raise NotFoundError("Item not found")
        return {"success": True, "message": "Item availability updated successfully"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("items.availability.failed error=%s", str(e))
        return {"success": False, "message": "Failed to update availability", "error_code": "INTERNAL_ERROR"}


@router.delete("/{item_id}", response_model=BaseResponse)
async def delete_item(
    item_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a menu item scoped to persona."""
    try:
        deleted = await ItemService(db).soft_delete_item(item_id, persona_id)
        if not deleted:
            raise NotFoundError("Item not found")
        return {"success": True, "message": "Item deleted successfully"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("items.delete.failed error=%s", str(e))
        return {"success": False, "message": "Failed to delete item", "error_code": "INTERNAL_ERROR"}


@router.post("/{item_id}/image", response_model=BaseResponse)
async def upload_item_image(
    item_id: int,
    persona_id: int = Query(..., ge=1),
    file: UploadFile = File(..., description="Image file (JPEG, PNG, WebP, GIF — max 5 MB)"),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:update")),
    db: AsyncSession = Depends(get_db),
):
    """Upload or replace the image for a menu item."""
    try:
        workspace_id = current_user.get("workspace_id")
        if not workspace_id:
            raise BadRequestError("workspace_id could not be resolved for this user")

        file_data = await file.read()
        url = await ItemService(db).upload_image(
            item_id=item_id,
            persona_id=persona_id,
            workspace_id=workspace_id,
            file_data=file_data,
            content_type=file.content_type or "",
        )
        return {"success": True, "message": "Image uploaded successfully", "data": {"image_url": url}}
    except BadRequestError as e:
        return {"success": False, "message": str(e), "error_code": "BAD_REQUEST"}
    except Exception as e:
        logger.exception("items.image.failed error=%s", str(e))
        return {"success": False, "message": "Failed to upload image", "error_code": "INTERNAL_ERROR"}


@router.post("/{item_id}/restore", response_model=BaseResponse)
async def restore_item(
    item_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("items:restore")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted menu item scoped to persona. Requires 'items:restore' permission."""
    try:
        restored = await ItemService(db).restore_item(item_id, persona_id)
        if not restored:
            raise NotFoundError("Item not found or is not deleted")
        return {"success": True, "message": "Item restored successfully"}
    except PermissionDeniedError:
        return {
            "success": False,
            "message": "You do not have permission to restore items",
            "error_code": "PERMISSION_DENIED",
        }
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("items.restore.failed error=%s", str(e))
        return {"success": False, "message": "Failed to restore item", "error_code": "INTERNAL_ERROR"}
