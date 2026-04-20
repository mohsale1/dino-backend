from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.repositories.AreaRepository import AreaRepository
from src.repositories.CategoryRepository import CategoryRepository
from src.repositories.ItemRepository import ItemRepository
from src.repositories.PersonaRepository import PersonaRepository
from src.repositories.TableRepository import TableRepository
from src.schemas.Area import AreaCreate, AreaUpdate, AreaResponse
from src.schemas.Category import CategoryCreate, CategoryUpdate, CategoryResponse
from src.schemas.Item import ItemCreate, ItemUpdate, ItemResponse
from src.schemas.Table import TableCreate, TableUpdate, TableResponse

router = APIRouter(prefix="/menu", tags=["Application Menu Management"])


# ==================== AREAS ====================

@router.post("/areas", response_model=BaseResponse)
async def create_area(
    area: AreaCreate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('areas:create')),
    db: AsyncSession = Depends(get_db),
):
    """Create new area (Admin only)."""
    repo = AreaRepository(db)

    area_data = area.model_dump()
    area_data["workspace_id"] = user.get("workspace_id")

    result = await repo.create(area_data)
    area_id = result.get("id") if isinstance(result, dict) else result

    return {
        "success": True,
        "message": "Area created successfully",
        "data": {"id": area_id},
    }


@router.get("/areas")
async def get_areas(
    page: int = 1,
    page_size: int = 10,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('areas:read')),
    db: AsyncSession = Depends(get_db),
):
    """Get all areas (All roles)."""
    repo = AreaRepository(db)

    # Only filter by persona_id if the user actually has one (Admin sees all)
    persona_id = user.get("persona_id")
    filters: Dict[str, Any] = {"persona_id": persona_id} if persona_id else {}

    items, total, total_pages = await repo.get_paginated(
        page=page,
        page_size=page_size,
        filters=filters,
        order_by="display_order",
        order_direction="asc",
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
            "has_prev": page > 1,
        },
    }


@router.get("/areas/{area_id}", response_model=BaseResponse)
async def get_area(
    area_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('areas:read')),
    db: AsyncSession = Depends(get_db),
):
    """Get area details."""
    repo = AreaRepository(db)

    area = await repo.get_by_id(area_id)

    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found",
        )

    return {
        "success": True,
        "message": "Area retrieved successfully",
        "data": area,
    }


@router.put("/areas/{area_id}", response_model=BaseResponse)
async def update_area(
    area_id: int,
    area: AreaUpdate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('areas:update')),
    db: AsyncSession = Depends(get_db),
):
    """Update area (Admin only)."""
    repo = AreaRepository(db)

    success = await repo.update(area_id, area.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found",
        )

    return {
        "success": True,
        "message": "Area updated successfully",
    }


@router.delete("/areas/{area_id}", response_model=BaseResponse)
async def delete_area(
    area_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('areas:delete')),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete area (Admin only)."""
    repo = AreaRepository(db)

    success = await repo.soft_delete(area_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found",
        )

    return {
        "success": True,
        "message": "Area deleted successfully",
    }


# ==================== TABLES ====================

@router.post("/tables", response_model=BaseResponse)
async def create_table(
    table: TableCreate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('tables:create')),
    db: AsyncSession = Depends(get_db),
):
    """Create new table (Admin only)."""
    repo = TableRepository(db)

    table_data = table.model_dump()
    table_data["workspace_id"] = user.get("workspace_id")

    result = await repo.create(table_data)
    table_id = result.get("id") if isinstance(result, dict) else result

    return {
        "success": True,
        "message": "Table created successfully",
        "data": {"id": table_id},
    }


@router.get("/tables")
async def get_tables(
    page: int = 1,
    page_size: int = 10,
    area_id: Optional[int] = None,
    status: Optional[str] = None,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('tables:read')),
    db: AsyncSession = Depends(get_db),
):
    """Get all tables (All roles)."""
    repo = TableRepository(db)

    # Only filter by persona_id if the user actually has one (Admin sees all)
    persona_id = user.get("persona_id")
    filters: Dict[str, Any] = {"persona_id": persona_id} if persona_id else {}

    if area_id:
        filters["area_id"] = area_id
    if status:
        filters["status"] = status

    items, total, total_pages = await repo.get_paginated(
        page=page,
        page_size=page_size,
        filters=filters,
        order_by="display_order",
        order_direction="asc",
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
            "has_prev": page > 1,
        },
    }


@router.get("/tables/{table_id}", response_model=BaseResponse)
async def get_table(
    table_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('tables:read')),
    db: AsyncSession = Depends(get_db),
):
    """Get table details."""
    repo = TableRepository(db)

    table = await repo.get_by_id(table_id)

    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found",
        )

    return {
        "success": True,
        "message": "Table retrieved successfully",
        "data": table,
    }


@router.put("/tables/{table_id}", response_model=BaseResponse)
async def update_table(
    table_id: int,
    table: TableUpdate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('tables:update')),
    db: AsyncSession = Depends(get_db),
):
    """Update table (Admin only)."""
    repo = TableRepository(db)

    success = await repo.update(table_id, table.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found",
        )

    return {
        "success": True,
        "message": "Table updated successfully",
    }


@router.delete("/tables/{table_id}", response_model=BaseResponse)
async def delete_table(
    table_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('tables:delete')),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete table (Admin only)."""
    repo = TableRepository(db)

    success = await repo.soft_delete(table_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found",
        )

    return {
        "success": True,
        "message": "Table deleted successfully",
    }


# ==================== CATEGORIES ====================

@router.post("/categories", response_model=BaseResponse)
async def create_category(
    category: CategoryCreate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('categories:create')),
    db: AsyncSession = Depends(get_db),
):
    """Create new category (Admin only)."""
    repo = CategoryRepository(db)

    category_data = category.model_dump()
    category_data["workspace_id"] = user.get("workspace_id")

    result = await repo.create(category_data)
    category_id = result.get("id") if isinstance(result, dict) else result

    return {
        "success": True,
        "message": "Category created successfully",
        "data": {"id": category_id},
    }


@router.get("/categories")
async def get_categories(
    page: int = 1,
    page_size: int = 10,
    parent_only: bool = False,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('categories:read')),
    db: AsyncSession = Depends(get_db),
):
    """Get all categories (All roles)."""
    repo = CategoryRepository(db)

    # Only filter by persona_id if the user actually has one (Admin sees all)
    persona_id = user.get("persona_id")
    filters: Dict[str, Any] = {"persona_id": persona_id} if persona_id else {}

    if parent_only:
        # Fetch all categories for this scope, then filter root ones (parent_id is None)
        # in Python — SQL NULL equality via dict filters is unreliable across repos.
        all_categories = await repo.get_all(
            filters=filters,
            order_by="display_order",
            order_direction="asc",
        )
        root_categories = [c for c in all_categories if not c.get("parent_id")]
        return {
            "success": True,
            "message": "Categories retrieved successfully",
            "data": root_categories,
        }

    items, total, total_pages = await repo.get_paginated(
        page=page,
        page_size=page_size,
        filters=filters,
        order_by="display_order",
        order_direction="asc",
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


@router.get("/categories/{category_id}", response_model=BaseResponse)
async def get_category(
    category_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('categories:read')),
    db: AsyncSession = Depends(get_db),
):
    """Get category details."""
    repo = CategoryRepository(db)

    category = await repo.get_by_id(category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return {
        "success": True,
        "message": "Category retrieved successfully",
        "data": category,
    }


@router.put("/categories/{category_id}", response_model=BaseResponse)
async def update_category(
    category_id: int,
    category: CategoryUpdate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('categories:update')),
    db: AsyncSession = Depends(get_db),
):
    """Update category (Admin only)."""
    repo = CategoryRepository(db)

    success = await repo.update(category_id, category.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return {
        "success": True,
        "message": "Category updated successfully",
    }


@router.delete("/categories/{category_id}", response_model=BaseResponse)
async def delete_category(
    category_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('categories:delete')),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete category (Admin only)."""
    repo = CategoryRepository(db)

    success = await repo.soft_delete(category_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return {
        "success": True,
        "message": "Category deleted successfully",
    }


# ==================== ITEMS ====================

@router.post("/items", response_model=BaseResponse)
async def create_item(
    item: ItemCreate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('items:create')),
    db: AsyncSession = Depends(get_db),
):
    """Create new item (Admin only)."""
    repo = ItemRepository(db)

    item_data = item.model_dump()
    item_data["workspace_id"] = user.get("workspace_id")

    result = await repo.create(item_data)
    item_id = result.get("id") if isinstance(result, dict) else result

    return {
        "success": True,
        "message": "Item created successfully",
        "data": {"id": item_id},
    }


@router.get("/items")
async def get_items(
    page: int = 1,
    page_size: int = 10,
    category_id: Optional[int] = None,
    available_only: bool = False,
    featured_only: bool = False,
    search: Optional[str] = None,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('items:read')),
    db: AsyncSession = Depends(get_db),
):
    """Get all items (All roles)."""
    repo = ItemRepository(db)

    # Delegate search and featured filtering to the paginated workspace query
    # which supports search_query and is_available natively in SQL.
    workspace_id = user.get("workspace_id")

    if search or featured_only:
        items, total, total_pages = await repo.get_paginated_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            category_id=category_id,
            is_available=True if (featured_only or available_only) else None,
            search_query=search,
            order_by="display_order",
            order_direction="asc",
        )
        label = "Featured items" if featured_only else "Items"
        return {
            "success": True,
            "message": f"{label} retrieved successfully",
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

    # Only filter by persona_id if the user actually has one (Admin sees all)
    persona_id = user.get("persona_id")
    filters: Dict[str, Any] = {"persona_id": persona_id} if persona_id else {}

    if category_id:
        filters["category_id"] = category_id
    if available_only:
        filters["is_available"] = True

    items, total, total_pages = await repo.get_paginated(
        page=page,
        page_size=page_size,
        filters=filters,
        order_by="display_order",
        order_direction="asc",
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


@router.get("/items/{item_id}", response_model=BaseResponse)
async def get_item(
    item_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('items:read')),
    db: AsyncSession = Depends(get_db),
):
    """Get item details."""
    repo = ItemRepository(db)

    item = await repo.get_by_id(item_id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    return {
        "success": True,
        "message": "Item retrieved successfully",
        "data": item,
    }


@router.put("/items/{item_id}", response_model=BaseResponse)
async def update_item(
    item_id: int,
    item: ItemUpdate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('items:update')),
    db: AsyncSession = Depends(get_db),
):
    """Update item (Admin only)."""
    repo = ItemRepository(db)

    success = await repo.update(item_id, item.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    return {
        "success": True,
        "message": "Item updated successfully",
    }


@router.delete("/items/{item_id}", response_model=BaseResponse)
async def delete_item(
    item_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('items:delete')),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete item (Admin only)."""
    repo = ItemRepository(db)

    success = await repo.soft_delete(item_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    return {
        "success": True,
        "message": "Item deleted successfully",
    }


# ==================== PUBLIC MENU ENDPOINTS ====================

@router.get("/public/{persona_id}/{table_id}/validate")
async def validate_table_access(
    persona_id: int,
    table_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate table access for public menu.
    Public endpoint - no authentication required.
    """
    persona_repo = PersonaRepository(db)
    table_repo = TableRepository(db)

    persona = await persona_repo.get_by_id(persona_id)
    if not persona or not persona.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found or inactive",
        )

    table = await table_repo.get_by_id(table_id)
    if not table or not table.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive",
        )

    return {
        "success": True,
        "message": "Access validated successfully",
        "data": {
            "persona": {
                "id": persona.get("id"),
                "name": persona.get("name"),
                "description": persona.get("description"),
            },
            "table": {
                "id": table.get("id"),
                "table_number": table.get("table_number"),
                "area_id": table.get("area_id"),
                "capacity": table.get("capacity"),
                "status": table.get("status"),
            },
        },
    }


@router.get("/public/{persona_id}/{table_id}/categories")
async def get_public_categories(
    persona_id: int,
    table_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get menu categories for public viewing.
    Public endpoint - no authentication required.
    """
    persona_repo = PersonaRepository(db)
    table_repo = TableRepository(db)
    category_repo = CategoryRepository(db)

    persona = await persona_repo.get_by_id(persona_id)
    if not persona or not persona.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found or inactive",
        )

    table = await table_repo.get_by_id(table_id)
    if not table or not table.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive",
        )

    workspace_id = persona.get("workspace_id")

    categories = await category_repo.get_all(
        filters={
            "workspace_id": workspace_id,
            "is_available": True,
            "is_active": True,
        },
        order_by="display_order",
        order_direction="asc",
    )

    return {
        "success": True,
        "message": "Categories retrieved successfully",
        "data": categories,
    }


@router.get("/public/{persona_id}/{table_id}/items")
async def get_public_items(
    persona_id: int,
    table_id: int,
    category_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get menu items for public viewing.
    Public endpoint - no authentication required.
    """
    persona_repo = PersonaRepository(db)
    table_repo = TableRepository(db)
    item_repo = ItemRepository(db)

    persona = await persona_repo.get_by_id(persona_id)
    if not persona or not persona.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found or inactive",
        )

    table = await table_repo.get_by_id(table_id)
    if not table or not table.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive",
        )

    workspace_id = persona.get("workspace_id")

    filters: Dict[str, Any] = {
        "workspace_id": workspace_id,
        "is_available": True,
        "is_active": True,
    }

    if category_id:
        filters["category_id"] = category_id

    items = await item_repo.get_all(
        filters=filters,
        order_by="display_order",
        order_direction="asc",
    )

    return {
        "success": True,
        "message": "Items retrieved successfully",
        "data": items,
    }


@router.get("/public/{persona_id}/{table_id}/menu")
async def get_public_menu(
    persona_id: int,
    table_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete menu (categories + items) for public viewing.
    Public endpoint - no authentication required.
    """
    persona_repo = PersonaRepository(db)
    table_repo = TableRepository(db)
    category_repo = CategoryRepository(db)
    item_repo = ItemRepository(db)
    area_repo = AreaRepository(db)

    persona = await persona_repo.get_by_id(persona_id)
    if not persona or not persona.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found or inactive",
        )

    table = await table_repo.get_by_id(table_id)
    if not table or not table.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive",
        )

    workspace_id = persona.get("workspace_id")

    area = None
    if table.get("area_id"):
        area = await area_repo.get_by_id(table.get("area_id"))

    categories = await category_repo.get_all(
        filters={
            "workspace_id": workspace_id,
            "is_available": True,
            "is_active": True,
        },
        order_by="display_order",
        order_direction="asc",
    )

    items = await item_repo.get_all(
        filters={
            "workspace_id": workspace_id,
            "is_available": True,
            "is_active": True,
        },
        order_by="display_order",
        order_direction="asc",
    )

    # Group items by category in Python (no extra DB round-trip needed)
    items_by_category: Dict[Any, List[Dict[str, Any]]] = {}
    for item in items:
        cat_id = item.get("category_id", "uncategorized")
        if cat_id not in items_by_category:
            items_by_category[cat_id] = []
        items_by_category[cat_id].append(item)

    return {
        "success": True,
        "message": "Menu retrieved successfully",
        "data": {
            "persona": {
                "id": persona.get("id"),
                "name": persona.get("name"),
                "description": persona.get("description"),
            },
            "table": {
                "id": table.get("id"),
                "table_number": table.get("table_number"),
                "area_id": table.get("area_id"),
                "capacity": table.get("capacity"),
                "status": table.get("status"),
            },
            "area": area,
            "categories": categories,
            "items": items,
            "items_by_category": items_by_category,
        },
    }
