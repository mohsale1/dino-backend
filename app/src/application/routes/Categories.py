"""
Categories router — CRUD for menu categories.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Category import CategoryService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/categories", tags=["Categories"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateCategoryRequest(BaseModel):
    name: str
    description: Optional[str] = None
    workspace_id: Optional[int] = None
    persona_id: Optional[int] = None
    image_url: Optional[str] = None
    is_available: bool = True
    display_order: Optional[int] = None


class UpdateCategoryRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    persona_id: Optional[int] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None
    display_order: Optional[int] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_categories(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    is_available: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated categories."""
    wid = workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = CategoryService(db)
    items, total, total_pages = await service.get_paginated_categories(
        workspace_id=wid,
        persona_id=persona_id,
        is_available=is_available,
        page=page,
        page_size=page_size,
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


@router.post("", response_model=BaseResponse)
async def create_category(
    request: CreateCategoryRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new category."""
    wid = request.workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = CategoryService(db)
    data = request.model_dump()
    data["workspace_id"] = wid
    category = await service.create_category(data)
    return {"success": True, "message": "Category created successfully", "data": category}


@router.get("/{category_id}", response_model=BaseResponse)
async def get_category(
    category_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a category by ID."""
    service = CategoryService(db)
    category = await service.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return {"success": True, "message": "Category retrieved successfully", "data": category}


@router.put("/{category_id}", response_model=BaseResponse)
async def update_category(
    category_id: int,
    request: UpdateCategoryRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a category."""
    service = CategoryService(db)
    existing = await service.get_by_id(category_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    data = request.model_dump(exclude_unset=True)
    success = await service.update_category(category_id, data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return {"success": True, "message": "Category updated successfully"}


@router.delete("/{category_id}", response_model=BaseResponse)
async def delete_category(
    category_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a category."""
    service = CategoryService(db)
    existing = await service.get_by_id(category_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    success = await service.soft_delete_category(category_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return {"success": True, "message": "Category deleted successfully"}


@router.post("/{category_id}/restore", response_model=BaseResponse)
async def restore_category(
    category_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:update")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted category."""
    service = CategoryService(db)
    existing = await service.get_by_id(category_id, include_deleted=True)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if existing.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category is not deleted")
    success = await service.restore_category(category_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return {"success": True, "message": "Category restored successfully"}
