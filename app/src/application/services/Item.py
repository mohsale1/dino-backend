"""
ItemService — business logic for menu items.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.ItemRepository import ItemRepository


class ItemService(BaseService):
    """Service for managing menu items."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.item_repo = ItemRepository(db)
        super().__init__(self.item_repo)

    async def create_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new menu item."""
        data.setdefault("is_active", True)
        data.setdefault("is_available", True)
        return await self.item_repo.create(data)

    async def get_paginated_items(
        self,
        workspace_id: int,
        category_id: Optional[int] = None,
        is_available: Optional[bool] = None,
        is_vegetarian: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated items with optional filters."""
        return await self.item_repo.get_paginated_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            category_id=category_id,
            is_available=is_available,
            is_vegetarian=is_vegetarian,
            search_query=search,
        )

    async def update_item(self, item_id: int, data: Dict[str, Any]) -> bool:
        """Update a menu item by ID."""
        return await self.item_repo.update(item_id, data)

    async def update_availability(self, item_id: int, is_available: bool) -> bool:
        """Toggle the availability of a menu item."""
        return await self.item_repo.update(item_id, {"is_available": is_available})

    async def soft_delete_item(self, item_id: int) -> bool:
        """Soft-delete a menu item."""
        return await self.item_repo.soft_delete(item_id)

    async def restore_item(self, item_id: int) -> bool:
        """Restore a soft-deleted menu item."""
        return await self.item_repo.restore(item_id)
