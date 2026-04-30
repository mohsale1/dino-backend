"""
Categories router — CRUD for menu categories.
All endpoints are scoped by both workspace_id (from JWT) and persona_id (required query/body param).
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
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
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    persona_id: int = Field(..., ge=1)
    image_url: Optional[str] = Field(None, max_length=500)
    is_available: bool = True


class UpdateCategoryRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    is_available: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_workspace(current_user: Dict[str, Any]) -> int:
    wid = current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    return wid


def _require_persona(persona_id: Optional[int]) -> int:
    if persona_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="persona_id required")
    return persona_id


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_categories(
    persona_id: int = Query(..., ge=1),
    is_available: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated categories scoped to the user's workspace and persona."""
    wid = _require_workspace(current_user)
    _require_persona(persona_id)
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


@router.post("", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: CreateCategoryRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new category in the authenticated user's workspace, bound to a persona."""
    wid = _require_workspace(current_user)
    _require_persona(request.persona_id)
    service = CategoryService(db)
    data = request.model_dump()
    data["workspace_id"] = wid
    category = await service.create_category(data)
    return {"success": True, "message": "Category created successfully", "data": category}


@router.get("/{category_id}", response_model=BaseResponse)
async def get_category(
    category_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single category scoped to the user's workspace and persona."""
    wid = _require_workspace(current_user)
    _require_persona(persona_id)
    service = CategoryService(db)
    category = await service.get_category_for_persona(category_id, wid, persona_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return {"success": True, "message": "Category retrieved successfully", "data": category}


@router.put("/{category_id}", response_model=BaseResponse)
async def update_category(
    category_id: int,
    request: UpdateCategoryRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a category. Ownership enforced via workspace_id + persona_id in a single DB query."""
    wid = _require_workspace(current_user)
    _require_persona(persona_id)
    data = request.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided to update")

    service = CategoryService(db)
    updated = await service.update_category(category_id, wid, persona_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return {"success": True, "message": "Category updated successfully"}


@router.delete("/{category_id}", response_model=BaseResponse)
async def delete_category(
    category_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a category. Ownership enforced via workspace_id + persona_id in a single DB query."""
    wid = _require_workspace(current_user)
    _require_persona(persona_id)
    service = CategoryService(db)
    deleted = await service.soft_delete_category(category_id, wid, persona_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return {"success": True, "message": "Category deleted successfully"}


@router.post("/{category_id}/restore", response_model=BaseResponse)
async def restore_category(
    category_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("categories:update")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted category. Ownership and state enforced via workspace_id + persona_id in a single DB query."""
    wid = _require_workspace(current_user)
    _require_persona(persona_id)
    service = CategoryService(db)
    restored = await service.restore_category(category_id, wid, persona_id)
    if not restored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or is not deleted",
        )
    return {"success": True, "message": "Category restored successfully"}