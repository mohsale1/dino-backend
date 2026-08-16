"""
Categories router — CRUD for menu categories, scoped by persona_id.
"""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Category import CategoryService
from src.schemas.Category import CategoryCreate, CategoryUpdate
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=BaseResponse)
async def get_categories(
    persona_id: int = Query(..., ge=1),
    is_available: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated categories scoped to persona."""
    try:
        items, total, total_pages = await CategoryService(db).get_paginated_categories(
            persona_id=persona_id, is_available=is_available, page=page, page_size=page_size
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
    except Exception as e:
        logger.exception("categories.list.failed persona_id=%s error=%s", persona_id, str(e))
        return {"success": False, "message": "Failed to retrieve categories", "error_code": "INTERNAL_ERROR"}


@router.post("", response_model=BaseResponse, status_code=201)
async def create_category(
    request: CategoryCreate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new category scoped to persona."""
    try:
        category = await CategoryService(db).create_category(request.model_dump())
        return {"success": True, "message": "Category created successfully", "data": category}
    except PermissionDeniedError:
        return {"success": False, "message": "You do not have permission to create categories", "error_code": "PERMISSION_DENIED"}
    except Exception as e:
        logger.exception("categories.create.failed error=%s", str(e))
        return {"success": False, "message": "Failed to create category", "error_code": "INTERNAL_ERROR"}


@router.get("/{category_id}", response_model=BaseResponse)
async def get_category(
    category_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single category scoped to persona."""
    try:
        category = await CategoryService(db).get_category_for_persona(category_id, persona_id)
        if not category:
            raise NotFoundError("Category not found")
        return {"success": True, "message": "Category retrieved successfully", "data": category}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("categories.get.failed error=%s", str(e))
        return {"success": False, "message": "Failed to retrieve category", "error_code": "INTERNAL_ERROR"}


@router.put("/{category_id}", response_model=BaseResponse)
async def update_category(
    category_id: int,
    request: CategoryUpdate,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a category scoped to persona."""
    try:
        data = request.model_dump(exclude_unset=True)
        if not data:
            raise BadRequestError("No fields provided to update")

        updated = await CategoryService(db).update_category(category_id, persona_id, data)
        if not updated:
            raise NotFoundError("Category not found")
        return {"success": True, "message": "Category updated successfully"}
    except BadRequestError as e:
        return {"success": False, "message": str(e), "error_code": "BAD_REQUEST"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("categories.update.failed error=%s", str(e))
        return {"success": False, "message": "Failed to update category", "error_code": "INTERNAL_ERROR"}


@router.delete("/{category_id}", response_model=BaseResponse)
async def delete_category(
    category_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a category scoped to persona."""
    try:
        deleted = await CategoryService(db).soft_delete_category(category_id, persona_id)
        if not deleted:
            raise NotFoundError("Category not found")
        return {"success": True, "message": "Category deleted successfully"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("categories.delete.failed error=%s", str(e))
        return {"success": False, "message": "Failed to delete category", "error_code": "INTERNAL_ERROR"}


@router.post("/{category_id}/restore", response_model=BaseResponse)
async def restore_category(
    category_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:restore")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted category scoped to persona."""
    try:
        restored = await CategoryService(db).restore_category(category_id, persona_id)
        if not restored:
            raise NotFoundError("Category not found or is not deleted")
        return {"success": True, "message": "Category restored successfully"}
    except PermissionDeniedError:
        return {"success": False, "message": "You do not have permission to restore categories", "error_code": "PERMISSION_DENIED"}
    except NotFoundError as e:
        return {"success": False, "message": str(e), "error_code": "NOT_FOUND"}
    except Exception as e:
        logger.exception("categories.restore.failed error=%s", str(e))
        return {"success": False, "message": "Failed to restore category", "error_code": "INTERNAL_ERROR"}
