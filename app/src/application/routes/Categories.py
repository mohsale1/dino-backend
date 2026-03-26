from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.schemas.Category import CategoryCreate, CategoryUpdate, CategoryResponse
from src.application.services.Category import CategoryService
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationRoleCheck
from typing import Optional

router = APIRouter(prefix="/categories", tags=["Application Categories"])

@router.post("", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def create_category(category: CategoryCreate):
    """Create new category (Admin only)"""
    service = CategoryService()
    
    category_id = service.create_category(category.model_dump())
    
    return {
        "success": True,
        "message": "Category created successfully",
        "data": {"id": category_id}
    }

@router.get("", dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_all_categories(
    workspace_id: str = Query(..., description="Workspace ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    is_available: Optional[bool] = Query(None, description="Filter by availability"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Order direction (asc/desc)")
):
    """
    Get all categories with pagination
    
    Query Parameters:
    - workspace_id: Workspace ID (required)
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - is_available: Filter by availability
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    """
    service = CategoryService()
    
    if page_size > 100:
        page_size = 100
    
    items, total, total_pages = service.get_paginated_categories(
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
        is_available=is_available,
        order_by=order_by,
        order_direction=order_direction
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
            "has_prev": page > 1
        }
    }

@router.get("/{category_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_category(category_id: str):
    """Get category by ID"""
    service = CategoryService()
    
    category = service.get_category_by_id(category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return {
        "success": True,
        "message": "Category retrieved successfully",
        "data": category
    }

@router.put("/{category_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def update_category(category_id: str, category: CategoryUpdate):
    """Update category (Admin only)"""
    service = CategoryService()
    
    # Check if category exists
    existing_category = service.get_category_by_id(category_id)
    if not existing_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    success = service.update_category(category_id, category.model_dump(exclude_unset=True))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return {
        "success": True,
        "message": "Category updated successfully"
    }

@router.delete("/{category_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def delete_category(category_id: str):
    """Soft delete category (Admin only)"""
    service = CategoryService()
    
    # Check if category exists
    category = service.get_category_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    success = service.soft_delete_category(category_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return {
        "success": True,
        "message": "Category soft deleted successfully"
    }

@router.put("/{category_id}/restore", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def restore_category(category_id: str):
    """Restore soft-deleted category (Admin only)"""
    service = CategoryService()
    
    # Check if category exists (including deleted)
    category = service.get_category_by_id(category_id, include_deleted=True)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    if not category.get('is_deleted', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category is not deleted"
        )
    
    success = service.restore_category(category_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return {
        "success": True,
        "message": "Category restored successfully"
    }

@router.get("/{category_id}/items", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_category_items(
    category_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    is_available: Optional[bool] = Query(None, description="Filter by availability")
):
    """Get all items in a category"""
    from src.application.services.Item import ItemService
    
    category_service = CategoryService()
    item_service = ItemService()
    
    # Check if category exists
    category = category_service.get_category_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    if page_size > 100:
        page_size = 100
    
    items, total, total_pages = item_service.get_paginated_items(
        workspace_id=category.get('workspace_id'),
        page=page,
        page_size=page_size,
        category_id=category_id,
        is_available=is_available,
        order_by="created_at",
        order_direction="desc"
    )
    
    return {
        "success": True,
        "message": "Category items retrieved successfully",
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

@router.get("/{category_id}/items-count", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_category_items_count(category_id: str):
    """Get count of items in a category"""
    from src.repositories.ItemRepository import ItemRepository
    
    category_service = CategoryService()
    item_repo = ItemRepository()
    
    # Check if category exists
    category = category_service.get_category_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Get items count
    items = item_repo.get_all(filters={
        "category_id": category_id,
        "is_deleted": False
    })
    
    available_items = [item for item in items if item.get('is_available', False)]
    
    return {
        "success": True,
        "message": "Category items count retrieved successfully",
        "data": {
            "total_items": len(items),
            "available_items": len(available_items),
            "unavailable_items": len(items) - len(available_items)
        }
    }

@router.put("/{category_id}/availability", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_manager)])
async def toggle_category_availability(
    category_id: str,
    is_available: bool = Query(..., description="Availability status")
):
    """Toggle category availability (Admin, Manager)"""
    service = CategoryService()
    
    # Check if category exists
    category = service.get_category_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    success = service.update_category(category_id, {"is_available": is_available})
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return {
        "success": True,
        "message": f"Category {'enabled' if is_available else 'disabled'} successfully"
    }
