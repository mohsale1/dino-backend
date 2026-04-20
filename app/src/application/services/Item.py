from sqlalchemy.ext.asyncio import AsyncSession
from src.base.BaseService import BaseService
from src.repositories.ItemRepository import ItemRepository
from typing import Dict, Any, List, Tuple, Optional


class ItemService(BaseService):
    """Item service"""

    def __init__(self, db: AsyncSession):
        super().__init__(ItemRepository(db))

    async def create_item(self, data: Dict[str, Any]) -> str:
        """Create new item and return its ID"""
        result = await self.create(data)
        if isinstance(result, dict):
            return result.get('id')
        return result

    async def get_item_by_id(self, item_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get item by ID"""
        return await self.get_by_id(item_id, include_deleted)

    async def get_items_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all items by workspace"""
        return await self.repository.get_by_workspace(workspace_id)

    async def get_items_by_category(self, category_id: str) -> List[Dict[str, Any]]:
        """Get all items by category"""
        return await self.repository.get_by_category(category_id)

    async def get_paginated_items(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        category_id: Optional[str] = None,
        is_available: Optional[bool] = None,
        is_vegetarian: Optional[bool] = None,
        search_query: Optional[str] = None,
        order_by: str = 'created_at',
        order_direction: str = 'desc',
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated items"""
        return await self.repository.get_paginated_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            category_id=category_id,
            is_available=is_available,
            is_vegetarian=is_vegetarian,
            search_query=search_query,
            order_by=order_by,
            order_direction=order_direction,
        )

    async def update_item(self, item_id: str, data: Dict[str, Any]) -> bool:
        """Update item"""
        return await self.update(item_id, data)

    async def soft_delete_item(self, item_id: str) -> bool:
        """Soft delete item"""
        return await self.soft_delete(item_id)

    async def restore_item(self, item_id: str) -> bool:
        """Restore soft-deleted item"""
        return await self.restore(item_id)
