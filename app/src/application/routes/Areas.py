from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.schemas.Area import AreaCreate, AreaUpdate, AreaResponse
from src.repositories.AreaRepository import AreaRepository
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.config.Database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

router = APIRouter(prefix="/areas", tags=["Application Areas"])

@router.post("", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('areas:create'))])
async def create_area(
    area: AreaCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new area (Admin only)"""
    repo = AreaRepository(db)

    area_id = await repo.create(area.model_dump())
    if isinstance(area_id, dict):
        area_id = area_id.get('id')

    return {
        "success": True,
        "message": "Area created successfully",
        "data": {"id": area_id}
    }

@router.get("", dependencies=[Depends(ApplicationPermissionCheck.require('areas:read'))])
async def get_all_areas(
    workspace_id: int = Query(..., description="Workspace ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    is_available: Optional[bool] = Query(None, description="Filter by availability"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Order direction (asc/desc)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all areas with pagination

    Query Parameters:
    - workspace_id: Workspace ID (required)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - is_available: Filter by availability
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    """
    repo = AreaRepository(db)

    if page_size > 100:
        page_size = 100

    items, total, total_pages = await repo.get_paginated_by_workspace(
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
        is_available=is_available,
        order_by=order_by,
        order_direction=order_direction
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
            "has_prev": page > 1
        }
    }

@router.get("/{area_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('areas:read'))])
async def get_area(
    area_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get area by ID"""
    repo = AreaRepository(db)

    area = await repo.get_by_id(area_id)

    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )

    return {
        "success": True,
        "message": "Area retrieved successfully",
        "data": area
    }

@router.put("/{area_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('areas:update'))])
async def update_area(
    area_id: int,
    area: AreaUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update area (Admin only)"""
    repo = AreaRepository(db)

    # Check if area exists
    existing_area = await repo.get_by_id(area_id)
    if not existing_area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )

    success = await repo.update(area_id, area.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )

    return {
        "success": True,
        "message": "Area updated successfully"
    }

@router.delete("/{area_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('areas:delete'))])
async def delete_area(
    area_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete area (Admin only)"""
    repo = AreaRepository(db)

    # Check if area exists
    area = await repo.get_by_id(area_id)
    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )

    success = await repo.soft_delete(area_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )

    return {
        "success": True,
        "message": "Area soft deleted successfully"
    }

@router.put("/{area_id}/restore", response_model=BaseResponse, dependencies=[Depends(ApplicationPermissionCheck.require('areas:restore'))])
async def restore_area(
    area_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Restore soft-deleted area (Admin only)"""
    repo = AreaRepository(db)

    # Check if area exists (including deleted)
    area = await repo.get_by_id(area_id, include_deleted=True)
    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )

    if area.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Area is not deleted"
        )

    success = await repo.restore(area_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )

    return {
        "success": True,
        "message": "Area restored successfully"
    }
