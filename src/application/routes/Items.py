from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.schemas.Item import ItemCreate, ItemUpdate, ItemResponse
from src.application.services.Item import ItemService
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationRoleCheck
from typing import Optional, List

router = APIRouter(prefix="/items", tags=["Application Items"])

@router.post("", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def create_item(item: ItemCreate):
    """Create new item (Admin only)"""
    service = ItemService()
    
    item_id = service.create_item(item.model_dump())
    
    return {
        "success": True,
        "message": "Item created successfully",
        "data": {"id": item_id}
    }

@router.get("", dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_all_items(
    workspace_id: str = Query(..., description="Workspace ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    category_id: Optional[str] = Query(None, description="Filter by category"),
    is_available: Optional[bool] = Query(None, description="Filter by availability"),
    is_vegetarian: Optional[bool] = Query(None, description="Filter by veg/non-veg (True=Veg, False=Non-Veg)"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    order_by: str = Query("created_at", description="Field to order by"),
    order_direction: str = Query("desc", description="Order direction (asc/desc)")
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
    service = ItemService()
    
    if page_size > 100:
        page_size = 100
    
    items, total, total_pages = service.get_paginated_items(
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

@router.get("/{item_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_item(item_id: str):
    """Get item by ID"""
    service = ItemService()
    
    item = service.get_item_by_id(item_id)
    
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

@router.put("/{item_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def update_item(item_id: str, item: ItemUpdate):
    """Update item (Admin only)"""
    service = ItemService()
    
    # Check if item exists
    existing_item = service.get_item_by_id(item_id)
    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    success = service.update_item(item_id, item.model_dump(exclude_unset=True))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return {
        "success": True,
        "message": "Item updated successfully"
    }

@router.delete("/{item_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def delete_item(item_id: str):
    """Soft delete item (Admin only)"""
    service = ItemService()
    
    # Check if item exists
    item = service.get_item_by_id(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    success = service.soft_delete_item(item_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return {
        "success": True,
        "message": "Item soft deleted successfully"
    }

@router.put("/{item_id}/restore", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def restore_item(item_id: str):
    """Restore soft-deleted item (Admin only)"""
    service = ItemService()
    
    # Check if item exists (including deleted)
    item = service.get_item_by_id(item_id, include_deleted=True)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    if not item.get('is_deleted', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item is not deleted"
        )
    
    success = service.restore_item(item_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return {
        "success": True,
        "message": "Item restored successfully"
    }

@router.put("/{item_id}/availability", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_manager)])
async def toggle_item_availability(
    item_id: str,
    is_available: bool = Query(..., description="Availability status")
):
    """Toggle item availability (Admin, Manager)"""
    service = ItemService()
    
    # Check if item exists
    item = service.get_item_by_id(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    success = service.update_item(item_id, {"is_available": is_available})
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return {
        "success": True,
        "message": f"Item {'enabled' if is_available else 'disabled'} successfully"
    }

@router.post("/bulk-update-availability", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_manager)])
async def bulk_update_item_availability(
    item_ids: List[str],
    is_available: bool
):
    """Bulk update item availability (Admin, Manager)"""
    service = ItemService()
    
    updated_count = 0
    failed_items = []
    
    for item_id in item_ids:
        try:
            item = service.get_item_by_id(item_id)
            if not item:
                failed_items.append({"id": item_id, "reason": "Item not found"})
                continue
            
            success = service.update_item(item_id, {"is_available": is_available})
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

@router.post("/bulk-delete", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def bulk_delete_items(item_ids: List[str]):
    """Bulk soft delete items (Admin only)"""
    service = ItemService()
    
    deleted_count = 0
    failed_items = []
    
    for item_id in item_ids:
        try:
            item = service.get_item_by_id(item_id)
            if not item:
                failed_items.append({"id": item_id, "reason": "Item not found"})
                continue
            
            success = service.soft_delete_item(item_id)
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

@router.post("/bulk-update-category", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def bulk_update_item_category(
    item_ids: List[str],
    category_id: str
):
    """Bulk update item category (Admin only)"""
    service = ItemService()
    
    updated_count = 0
    failed_items = []
    
    for item_id in item_ids:
        try:
            item = service.get_item_by_id(item_id)
            if not item:
                failed_items.append({"id": item_id, "reason": "Item not found"})
                continue
            
            success = service.update_item(item_id, {"category_id": category_id})
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
