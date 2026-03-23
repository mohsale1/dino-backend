from fastapi import APIRouter, HTTPException, status, Depends
from src.schemas.Area import AreaCreate, AreaUpdate, AreaResponse
from src.schemas.Table import TableCreate, TableUpdate, TableResponse
from src.schemas.Category import CategoryCreate, CategoryUpdate, CategoryResponse
from src.schemas.Item import ItemCreate, ItemUpdate, ItemResponse
from src.repositories.AreaRepository import AreaRepository
from src.repositories.TableRepository import TableRepository
from src.repositories.CategoryRepository import CategoryRepository
from src.repositories.ItemRepository import ItemRepository
from src.repositories.OrganizationRepository import OrganizationRepository
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationRoleCheck
from typing import Dict, Any, List

router = APIRouter(prefix="/menu", tags=["Application Menu Management"])

# ==================== AREAS ====================

@router.post("/areas", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def create_area(area: AreaCreate, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin)):
    """Create new area (Admin only)"""
    repo = AreaRepository()
    
    # Add workspace_id from user
    area_data = area.model_dump()
    area_data['workspace_id'] = user.get('workspace_id')
    
    area_id = repo.create(area_data)
    
    return {
        "success": True,
        "message": "Area created successfully",
        "data": {"id": area_id}
    }

@router.get("/areas", dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_areas(
    page: int = 1,
    page_size: int = 10,
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """Get all areas (All roles)"""
    repo = AreaRepository()
    
    filters = {"organization_id": user.get('organization_id')}
    
    items, total, total_pages = repo.get_paginated(
        page=page,
        page_size=page_size,
        filters=filters,
        order_by="display_order",
        order_direction="asc"
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

@router.get("/areas/{area_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_area(area_id: str):
    """Get area details"""
    repo = AreaRepository()
    
    area = repo.get_by_id(area_id)
    
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

@router.put("/areas/{area_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def update_area(area_id: str, area: AreaUpdate):
    """Update area (Admin only)"""
    repo = AreaRepository()
    
    success = repo.update(area_id, area.model_dump(exclude_unset=True))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )
    
    return {
        "success": True,
        "message": "Area updated successfully"
    }

@router.delete("/areas/{area_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def delete_area(area_id: str):
    """Soft delete area (Admin only)"""
    repo = AreaRepository()
    
    success = repo.soft_delete(area_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found"
        )
    
    return {
        "success": True,
        "message": "Area deleted successfully"
    }

# ==================== TABLES ====================

@router.post("/tables", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def create_table(table: TableCreate, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin)):
    """Create new table (Admin only)"""
    repo = TableRepository()
    
    # Add workspace_id from user
    table_data = table.model_dump()
    table_data['workspace_id'] = user.get('workspace_id')
    
    table_id = repo.create(table_data)
    
    return {
        "success": True,
        "message": "Table created successfully",
        "data": {"id": table_id}
    }

@router.get("/tables", dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_tables(
    page: int = 1,
    page_size: int = 10,
    area_id: str = None,
    status: str = None,
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """Get all tables (All roles)"""
    repo = TableRepository()
    
    filters = {"organization_id": user.get('organization_id')}
    
    if area_id:
        filters['area_id'] = area_id
    if status:
        filters['status'] = status
    
    items, total, total_pages = repo.get_paginated(
        page=page,
        page_size=page_size,
        filters=filters,
        order_by="display_order",
        order_direction="asc"
    )
    
    return {
        "success": True,
        "message": "Tables retrieved successfully",
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

@router.get("/tables/{table_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_table(table_id: str):
    """Get table details"""
    repo = TableRepository()
    
    table = repo.get_by_id(table_id)
    
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    return {
        "success": True,
        "message": "Table retrieved successfully",
        "data": table
    }

@router.put("/tables/{table_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def update_table(table_id: str, table: TableUpdate):
    """Update table (Admin only)"""
    repo = TableRepository()
    
    success = repo.update(table_id, table.model_dump(exclude_unset=True))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    return {
        "success": True,
        "message": "Table updated successfully"
    }

@router.delete("/tables/{table_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def delete_table(table_id: str):
    """Soft delete table (Admin only)"""
    repo = TableRepository()
    
    success = repo.soft_delete(table_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    return {
        "success": True,
        "message": "Table deleted successfully"
    }

# ==================== CATEGORIES ====================

@router.post("/categories", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def create_category(category: CategoryCreate, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin)):
    """Create new category (Admin only)"""
    repo = CategoryRepository()
    
    # Add workspace_id from user
    category_data = category.model_dump()
    category_data['workspace_id'] = user.get('workspace_id')
    
    category_id = repo.create(category_data)
    
    return {
        "success": True,
        "message": "Category created successfully",
        "data": {"id": category_id}
    }

@router.get("/categories", dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_categories(
    page: int = 1,
    page_size: int = 10,
    parent_only: bool = False,
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """Get all categories (All roles)"""
    repo = CategoryRepository()
    
    if parent_only:
        # Get only root categories
        categories = repo.get_root_categories(user.get('organization_id'))
        return {
            "success": True,
            "message": "Categories retrieved successfully",
            "data": categories
        }
    
    filters = {"organization_id": user.get('organization_id')}
    
    items, total, total_pages = repo.get_paginated(
        page=page,
        page_size=page_size,
        filters=filters,
        order_by="display_order",
        order_direction="asc"
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

@router.get("/categories/{category_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_category(category_id: str):
    """Get category details"""
    repo = CategoryRepository()
    
    category = repo.get_by_id(category_id)
    
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

@router.put("/categories/{category_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def update_category(category_id: str, category: CategoryUpdate):
    """Update category (Admin only)"""
    repo = CategoryRepository()
    
    success = repo.update(category_id, category.model_dump(exclude_unset=True))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return {
        "success": True,
        "message": "Category updated successfully"
    }

@router.delete("/categories/{category_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def delete_category(category_id: str):
    """Soft delete category (Admin only)"""
    repo = CategoryRepository()
    
    success = repo.soft_delete(category_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return {
        "success": True,
        "message": "Category deleted successfully"
    }

# ==================== ITEMS ====================

@router.post("/items", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def create_item(item: ItemCreate, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin)):
    """Create new item (Admin only)"""
    repo = ItemRepository()
    
    # Add workspace_id from user
    item_data = item.model_dump()
    item_data['workspace_id'] = user.get('workspace_id')
    
    item_id = repo.create(item_data)
    
    return {
        "success": True,
        "message": "Item created successfully",
        "data": {"id": item_id}
    }

@router.get("/items", dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_items(
    page: int = 1,
    page_size: int = 10,
    category_id: str = None,
    available_only: bool = False,
    featured_only: bool = False,
    search: str = None,
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """Get all items (All roles)"""
    repo = ItemRepository()
    
    # Handle search
    if search:
        items = repo.search_items(user.get('organization_id'), search)
        return {
            "success": True,
            "message": "Items retrieved successfully",
            "data": items
        }
    
    # Handle featured items
    if featured_only:
        items = repo.get_featured_items(user.get('organization_id'))
        return {
            "success": True,
            "message": "Featured items retrieved successfully",
            "data": items
        }
    
    filters = {"organization_id": user.get('organization_id')}
    
    if category_id:
        filters['category_id'] = category_id
    if available_only:
        filters['is_available'] = True
    
    items, total, total_pages = repo.get_paginated(
        page=page,
        page_size=page_size,
        filters=filters,
        order_by="display_order",
        order_direction="asc"
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

@router.get("/items/{item_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_item(item_id: str):
    """Get item details"""
    repo = ItemRepository()
    
    item = repo.get_by_id(item_id)
    
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

@router.put("/items/{item_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def update_item(item_id: str, item: ItemUpdate):
    """Update item (Admin only)"""
    repo = ItemRepository()
    
    success = repo.update(item_id, item.model_dump(exclude_unset=True))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return {
        "success": True,
        "message": "Item updated successfully"
    }

@router.delete("/items/{item_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def delete_item(item_id: str):
    """Soft delete item (Admin only)"""
    repo = ItemRepository()
    
    success = repo.soft_delete(item_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return {
        "success": True,
        "message": "Item deleted successfully"
    }

# ==================== PUBLIC MENU ENDPOINTS ====================

@router.get("/public/{organization_id}/{table_id}/validate")
async def validate_table_access(organization_id: str, table_id: str):
    """
    Validate table access for public menu
    Public endpoint - no authentication required
    """
    org_repo = OrganizationRepository()
    table_repo = TableRepository()
    
    # Check organization exists and is active
    organization = org_repo.get_by_id(organization_id)
    if not organization or not organization.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive"
        )
    
    # Check table exists and is active
    table = table_repo.get_by_id(table_id)
    if not table or not table.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive"
        )
    
    return {
        "success": True,
        "message": "Access validated successfully",
        "data": {
            "organization": {
                "id": organization.get('id'),
                "name": organization.get('name'),
                "description": organization.get('description')
            },
            "table": {
                "id": table.get('id'),
                "table_number": table.get('table_number'),
                "area_id": table.get('area_id'),
                "capacity": table.get('capacity'),
                "status": table.get('status')
            }
        }
    }

@router.get("/public/{organization_id}/{table_id}/categories")
async def get_public_categories(organization_id: str, table_id: str):
    """
    Get menu categories for public viewing
    Public endpoint - no authentication required
    """
    org_repo = OrganizationRepository()
    table_repo = TableRepository()
    category_repo = CategoryRepository()
    
    # Validate access
    organization = org_repo.get_by_id(organization_id)
    if not organization or not organization.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive"
        )
    
    table = table_repo.get_by_id(table_id)
    if not table or not table.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive"
        )
    
    workspace_id = organization.get('workspace_id')
    
    # Get all active categories for this workspace
    categories = category_repo.get_all(
        filters={
            "workspace_id": workspace_id,
            "is_available": True,
            "is_active": True
        },
        order_by="display_order",
        order_direction="asc"
    )
    
    return {
        "success": True,
        "message": "Categories retrieved successfully",
        "data": categories
    }

@router.get("/public/{organization_id}/{table_id}/items")
async def get_public_items(
    organization_id: str, 
    table_id: str,
    category_id: str = None
):
    """
    Get menu items for public viewing
    Public endpoint - no authentication required
    """
    org_repo = OrganizationRepository()
    table_repo = TableRepository()
    item_repo = ItemRepository()
    
    # Validate access
    organization = org_repo.get_by_id(organization_id)
    if not organization or not organization.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive"
        )
    
    table = table_repo.get_by_id(table_id)
    if not table or not table.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive"
        )
    
    workspace_id = organization.get('workspace_id')
    
    # Build filters
    filters = {
        "workspace_id": workspace_id,
        "is_available": True,
        "is_active": True
    }
    
    if category_id:
        filters["category_id"] = category_id
    
    # Get all active items for this workspace
    items = item_repo.get_all(
        filters=filters,
        order_by="display_order",
        order_direction="asc"
    )
    
    return {
        "success": True,
        "message": "Items retrieved successfully",
        "data": items
    }

@router.get("/public/{organization_id}/{table_id}/menu")
async def get_public_menu(organization_id: str, table_id: str):
    """
    Get complete menu (categories + items) for public viewing
    Public endpoint - no authentication required
    """
    org_repo = OrganizationRepository()
    table_repo = TableRepository()
    category_repo = CategoryRepository()
    item_repo = ItemRepository()
    area_repo = AreaRepository()
    
    # Validate access
    organization = org_repo.get_by_id(organization_id)
    if not organization or not organization.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive"
        )
    
    table = table_repo.get_by_id(table_id)
    if not table or not table.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive"
        )
    
    workspace_id = organization.get('workspace_id')
    
    # Get area info
    area = None
    if table.get('area_id'):
        area = area_repo.get_by_id(table.get('area_id'))
    
    # Get all active categories
    categories = category_repo.get_all(
        filters={
            "workspace_id": workspace_id,
            "is_available": True,
            "is_active": True
        },
        order_by="display_order",
        order_direction="asc"
    )
    
    # Get all active items
    items = item_repo.get_all(
        filters={
            "workspace_id": workspace_id,
            "is_available": True,
            "is_active": True
        },
        order_by="display_order",
        order_direction="asc"
    )
    
    # Group items by category
    items_by_category = {}
    for item in items:
        cat_id = item.get('category_id', 'uncategorized')
        if cat_id not in items_by_category:
            items_by_category[cat_id] = []
        items_by_category[cat_id].append(item)
    
    return {
        "success": True,
        "message": "Menu retrieved successfully",
        "data": {
            "organization": {
                "id": organization.get('id'),
                "name": organization.get('name'),
                "description": organization.get('description')
            },
            "table": {
                "id": table.get('id'),
                "table_number": table.get('table_number'),
                "area_id": table.get('area_id'),
                "capacity": table.get('capacity'),
                "status": table.get('status')
            },
            "area": area,
            "categories": categories,
            "items": items,
            "items_by_category": items_by_category
        }
    }
