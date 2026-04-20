from sqlalchemy.ext.asyncio import AsyncSession
from src.base.BaseService import BaseService
from src.repositories.CategoryRepository import CategoryRepository
from typing import Dict, Any, List, Tuple, Optional


class CategoryService(BaseService):
    """Category service"""

    def __init__(self, db: AsyncSession):
        super().__init__(CategoryRepository(db))

    async def create_category(self, data: Dict[str, Any]) -> str:
        """Create new category and return its ID"""
        result = await self.create(data)
        if isinstance(result, dict):
            return result.get('id')
        return result

    async def get_category_by_id(self, category_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get category by ID"""
        return await self.get_by_id(category_id, include_deleted)

    async def get_categories_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all categories by workspace"""
        return await self.repository.get_by_workspace(workspace_id)

    async def get_paginated_categories(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        is_available: Optional[bool] = None,
        order_by: str = 'created_at',
        order_direction: str = 'desc',
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated categories"""
        return await self.repository.get_paginated_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            is_available=is_available,
            order_by=order_by,
            order_direction=order_direction,
        )

    async def update_category(self, category_id: str, data: Dict[str, Any]) -> bool:
        """Update category"""
        return await self.update(category_id, data)

    async def soft_delete_category(self, category_id: str) -> bool:
        """Soft delete category"""
        return await self.soft_delete(category_id)

    async def restore_category(self, category_id: str) -> bool:
        """Restore soft-deleted category"""
        return await self.restore(category_id)
