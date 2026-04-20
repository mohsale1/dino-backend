from typing import Dict, Any, List, Tuple, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.AreaRepository import AreaRepository


class AreaService(BaseService):
    """Area service"""

    def __init__(self, db: AsyncSession):
        super().__init__(AreaRepository(db))

    async def create_area(self, data: Dict[str, Any]) -> str:
        """Create new area and return its ID"""
        result = await self.create(data)
        if isinstance(result, dict):
            return result.get('id')
        return result

    async def get_area_by_id(self, area_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get area by ID"""
        return await self.get_by_id(area_id, include_deleted)

    async def get_areas_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all areas by workspace"""
        return await self.repository.get_by_workspace(workspace_id)

    async def get_paginated_areas(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        is_available: Optional[bool] = None,
        order_by: str = 'created_at',
        order_direction: str = 'desc',
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated areas"""
        return await self.repository.get_paginated_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            is_available=is_available,
            order_by=order_by,
            order_direction=order_direction,
        )

    async def update_area(self, area_id: str, data: Dict[str, Any]) -> bool:
        """Update area"""
        return await self.update(area_id, data)

    async def soft_delete_area(self, area_id: str) -> bool:
        """Soft delete area"""
        return await self.soft_delete(area_id)

    async def restore_area(self, area_id: str) -> bool:
        """Restore soft-deleted area"""
        return await self.restore(area_id)
