"""
Items router — CRUD for menu items, scoped by persona_id.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Item import ItemService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/items", tags=["Items"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateItemRequest(BaseModel):
    persona_id: int = Field(..., ge=1)
    category_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[str] = Field(None, max_length=500)
    price: Decimal = Field(..., ge=0)
    is_available: bool = True
    is_vegetarian: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class UpdateItemRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    image_url: Optional[str] = Field(None, max_length=500)
    price: Optional[Decimal] = Field(None, ge=0)
    is_available: Optional[bool] = None
    is_vegetarian: Optional[bool] = None
    category_id: Optional[int] = Field(None, ge=1)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class UpdateAvailabilityRequest(BaseModel):
    is_available: bool


# ---------------------------------------------------------------------------
# GET /items
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_items(
    persona_id: int = Query(..., ge=1),
    category_id: Optional[int] = Query(None, ge=1),
    is_available: Optional[bool] = Query(None),
    is_vegetarian: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated items scoped to persona with optional filters."""
    user_id = current_user.get("id")
    logger.info(
        "items.list.request user_id=%s persona_id=%s category_id=%s "
        "is_available=%s is_vegetarian=%s search=%r page=%s page_size=%s",
        user_id, persona_id, category_id, is_available, is_vegetarian, search, page, page_size,
    )

    items, total, total_pages = await ItemService(db).get_paginated_items(
        persona_id=persona_id,
        category_id=category_id,
        is_available=is_available,
        is_vegetarian=is_vegetarian,
        search=search,
        page=page,
        page_size=page_size,
    )

    logger.info(
        "items.list.response user_id=%s persona_id=%s total=%s page=%s total_pages=%s returned=%s",
        user_id, persona_id, total, page, total_pages, len(items),
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


# ---------------------------------------------------------------------------
# POST /items
# ---------------------------------------------------------------------------

@router.post("", response_model=BaseResponse, status_code=201)
async def create_item(
    request: CreateItemRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Create a new menu item scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "items.create.request user_id=%s persona_id=%s category_id=%s name=%r",
        user_id, request.persona_id, request.category_id, request.name,
    )

    # Use model_dump without exclude_none so null fields (description, image_url) are stored
    data = request.model_dump()
    item = await ItemService(db).create_item(data)

    logger.info(
        "items.create.response user_id=%s item_id=%s persona_id=%s category_id=%s name=%r",
        user_id, item.get("id"), request.persona_id, request.category_id, item.get("name"),
    )
    return {"success": True, "message": "Item created successfully", "data": item}


# ---------------------------------------------------------------------------
# GET /items/{item_id}
# ---------------------------------------------------------------------------

@router.get("/{item_id}", response_model=BaseResponse)
async def get_item(
    item_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a menu item by ID scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "items.get.request user_id=%s item_id=%s persona_id=%s",
        user_id, item_id, persona_id,
    )

    item = await ItemService(db).get_item_for_persona(item_id, persona_id)
    if not item:
        logger.warning(
            "items.get.not_found user_id=%s item_id=%s persona_id=%s",
            user_id, item_id, persona_id,
        )
        raise NotFoundError("Item not found")

    logger.info(
        "items.get.response user_id=%s item_id=%s persona_id=%s name=%r",
        user_id, item_id, persona_id, item.get("name"),
    )
    return {"success": True, "message": "Item retrieved successfully", "data": item}


# ---------------------------------------------------------------------------
# PUT /items/{item_id}
# ---------------------------------------------------------------------------

@router.put("/{item_id}", response_model=BaseResponse)
async def update_item(
    item_id: int,
    request: UpdateItemRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update a menu item scoped to persona."""
    user_id = current_user.get("id")
    data = request.model_dump(exclude_unset=True)

    if not data:
        logger.warning(
            "items.update.empty_payload user_id=%s item_id=%s persona_id=%s",
            user_id, item_id, persona_id,
        )
        raise BadRequestError("No fields provided for update")

    logger.info(
        "items.update.request user_id=%s item_id=%s persona_id=%s fields=%s",
        user_id, item_id, persona_id, list(data.keys()),
    )

    updated = await ItemService(db).update_item(item_id, persona_id, data)
    if not updated:
        logger.warning(
            "items.update.not_found user_id=%s item_id=%s persona_id=%s",
            user_id, item_id, persona_id,
        )
        raise NotFoundError("Item not found")

    logger.info(
        "items.update.response user_id=%s item_id=%s persona_id=%s fields=%s",
        user_id, item_id, persona_id, list(data.keys()),
    )
    return {"success": True, "message": "Item updated successfully"}


# ---------------------------------------------------------------------------
# PUT /items/{item_id}/availability
# ---------------------------------------------------------------------------

@router.put("/{item_id}/availability", response_model=BaseResponse)
async def update_item_availability(
    item_id: int,
    request: UpdateAvailabilityRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Toggle item availability scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "items.availability.request user_id=%s item_id=%s persona_id=%s is_available=%s",
        user_id, item_id, persona_id, request.is_available,
    )

    updated = await ItemService(db).update_availability(item_id, persona_id, request.is_available)
    if not updated:
        logger.warning(
            "items.availability.not_found user_id=%s item_id=%s persona_id=%s",
            user_id, item_id, persona_id,
        )
        raise NotFoundError("Item not found")

    logger.info(
        "items.availability.response user_id=%s item_id=%s persona_id=%s is_available=%s",
        user_id, item_id, persona_id, request.is_available,
    )
    return {"success": True, "message": "Item availability updated successfully"}


# ---------------------------------------------------------------------------
# DELETE /items/{item_id}
# ---------------------------------------------------------------------------

@router.delete("/{item_id}", response_model=BaseResponse)
async def delete_item(
    item_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a menu item scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "items.delete.request user_id=%s item_id=%s persona_id=%s",
        user_id, item_id, persona_id,
    )

    deleted = await ItemService(db).soft_delete_item(item_id, persona_id)
    if not deleted:
        logger.warning(
            "items.delete.not_found user_id=%s item_id=%s persona_id=%s",
            user_id, item_id, persona_id,
        )
        raise NotFoundError("Item not found")

    logger.info(
        "items.delete.response user_id=%s item_id=%s persona_id=%s",
        user_id, item_id, persona_id,
    )
    return {"success": True, "message": "Item deleted successfully"}


# ---------------------------------------------------------------------------
# POST /items/{item_id}/image
# ---------------------------------------------------------------------------

@router.post("/{item_id}/image", response_model=BaseResponse)
async def upload_item_image(
    item_id: int,
    persona_id: int = Query(..., ge=1),
    file: UploadFile = File(..., description="Image file (JPEG, PNG, WebP, GIF — max 5 MB)"),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload or replace the image for a menu item.

    - Stores to GCS at: items/{workspace_id}/{persona_id}/{item_id}_{persona_id}_{workspace_id}.{ext}
    - Re-uploading overwrites the same blob — no duplicate storage
    - Updates image_url on the item row
    - Allowed types: JPEG, PNG, WebP, GIF — max 5 MB
    """
    user_id = current_user.get("id")
    workspace_id = current_user.get("workspace_id")

    if not workspace_id:
        raise BadRequestError("workspace_id could not be resolved for this user")

    logger.info(
        "items.image.upload.request user_id=%s item_id=%s persona_id=%s "
        "workspace_id=%s filename=%r content_type=%s",
        user_id, item_id, persona_id, workspace_id,
        file.filename, file.content_type,
    )

    # Read file into memory — size validated inside the service/storage layer
    file_data = await file.read()

    url = await ItemService(db).upload_image(
        item_id=item_id,
        persona_id=persona_id,
        workspace_id=workspace_id,
        file_data=file_data,
        content_type=file.content_type or "",
    )

    logger.info(
        "items.image.upload.response user_id=%s item_id=%s persona_id=%s url=%s",
        user_id, item_id, persona_id, url,
    )
    return {
        "success": True,
        "message": "Image uploaded successfully",
        "data": {"image_url": url},
    }


# ---------------------------------------------------------------------------
# POST /items/{item_id}/restore
# ---------------------------------------------------------------------------

@router.post("/{item_id}/restore", response_model=BaseResponse)
async def restore_item(
    item_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted menu item scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "items.restore.request user_id=%s item_id=%s persona_id=%s",
        user_id, item_id, persona_id,
    )

    restored = await ItemService(db).restore_item(item_id, persona_id)
    if not restored:
        logger.warning(
            "items.restore.not_found user_id=%s item_id=%s persona_id=%s",
            user_id, item_id, persona_id,
        )
        raise NotFoundError("Item not found or is not deleted")

    logger.info(
        "items.restore.response user_id=%s item_id=%s persona_id=%s",
        user_id, item_id, persona_id,
    )
    return {"success": True, "message": "Item restored successfully"}
