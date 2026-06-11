"""
Categories router — CRUD for menu categories, scoped by persona_id.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Category import CategoryService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["Categories"])


class CreateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    persona_id: int = Field(..., ge=1)
    is_available: bool = True


class UpdateCategoryRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    is_available: Optional[bool] = None


@router.get("", response_model=BaseResponse)
async def get_categories(
    persona_id: int = Query(..., ge=1),
    is_available: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated categories scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "categories.list.request user_id=%s persona_id=%s is_available=%s page=%s page_size=%s",
        user_id, persona_id, is_available, page, page_size,
    )

    items, total, total_pages = await CategoryService(db).get_paginated_categories(
        persona_id=persona_id,
        is_available=is_available,
        page=page,
        page_size=page_size,
    )

    logger.info(
        "categories.list.response user_id=%s persona_id=%s total=%s page=%s total_pages=%s returned=%s",
        user_id, persona_id, total, page, total_pages, len(items),
    )
    return {
        "success": True,
        "message": "Categories retrieved successfully",
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
async def create_category(
    request: CreateCategoryRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Create a new category scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "categories.create.request user_id=%s persona_id=%s name=%r",
        user_id, request.persona_id, request.name,
    )

    data = request.model_dump()
    category = await CategoryService(db).create_category(data)

    logger.info(
        "categories.create.response user_id=%s persona_id=%s category_id=%s name=%r",
        user_id, request.persona_id, category.get("id"), category.get("name"),
    )
    return {"success": True, "message": "Category created successfully", "data": category}


@router.get("/{category_id}", response_model=BaseResponse)
async def get_category(
    category_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a single category scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "categories.get.request user_id=%s category_id=%s persona_id=%s",
        user_id, category_id, persona_id,
    )

    category = await CategoryService(db).get_category_for_persona(category_id, persona_id)
    if not category:
        logger.warning(
            "categories.get.not_found user_id=%s category_id=%s persona_id=%s",
            user_id, category_id, persona_id,
        )
        raise NotFoundError("Category not found")

    logger.info(
        "categories.get.response user_id=%s category_id=%s persona_id=%s name=%r",
        user_id, category_id, persona_id, category.get("name"),
    )
    return {"success": True, "message": "Category retrieved successfully", "data": category}


@router.put("/{category_id}", response_model=BaseResponse)
async def update_category(
    category_id: int,
    request: UpdateCategoryRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update a category scoped to persona."""
    user_id = current_user.get("id")
    data = request.model_dump(exclude_unset=True)

    if not data:
        logger.warning(
            "categories.update.empty_payload user_id=%s category_id=%s persona_id=%s",
            user_id, category_id, persona_id,
        )
        raise BadRequestError("No fields provided to update")

    logger.info(
        "categories.update.request user_id=%s category_id=%s persona_id=%s fields=%s",
        user_id, category_id, persona_id, list(data.keys()),
    )

    updated = await CategoryService(db).update_category(category_id, persona_id, data)
    if not updated:
        logger.warning(
            "categories.update.not_found user_id=%s category_id=%s persona_id=%s",
            user_id, category_id, persona_id,
        )
        raise NotFoundError("Category not found")

    logger.info(
        "categories.update.response user_id=%s category_id=%s persona_id=%s fields=%s",
        user_id, category_id, persona_id, list(data.keys()),
    )
    return {"success": True, "message": "Category updated successfully"}


@router.delete("/{category_id}", response_model=BaseResponse)
async def delete_category(
    category_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a category scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "categories.delete.request user_id=%s category_id=%s persona_id=%s",
        user_id, category_id, persona_id,
    )

    deleted = await CategoryService(db).soft_delete_category(category_id, persona_id)
    if not deleted:
        logger.warning(
            "categories.delete.not_found user_id=%s category_id=%s persona_id=%s",
            user_id, category_id, persona_id,
        )
        raise NotFoundError("Category not found")

    logger.info(
        "categories.delete.response user_id=%s category_id=%s persona_id=%s",
        user_id, category_id, persona_id,
    )
    return {"success": True, "message": "Category deleted successfully"}


@router.post("/{category_id}/restore", response_model=BaseResponse)
async def restore_category(
    category_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted category scoped to persona."""
    user_id = current_user.get("id")
    logger.info(
        "categories.restore.request user_id=%s category_id=%s persona_id=%s",
        user_id, category_id, persona_id,
    )

    restored = await CategoryService(db).restore_category(category_id, persona_id)
    if not restored:
        logger.warning(
            "categories.restore.not_found user_id=%s category_id=%s persona_id=%s",
            user_id, category_id, persona_id,
        )
        raise NotFoundError("Category not found or is not deleted")

    logger.info(
        "categories.restore.response user_id=%s category_id=%s persona_id=%s",
        user_id, category_id, persona_id,
    )
    return {"success": True, "message": "Category restored successfully"}
