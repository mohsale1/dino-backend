from sqlalchemy.ext.asyncio import AsyncSession
from src.base.BaseService import BaseService
from src.repositories.TableRepository import TableRepository
from typing import Dict, Any, List, Tuple, Optional


class TableService(BaseService):
    """Table service"""

    def __init__(self, db: AsyncSession):
        super().__init__(TableRepository(db))

    async def create_table(self, data: Dict[str, Any]) -> str:
        """Create new table and return its ID"""
        result = await self.create(data)
        if isinstance(result, dict):
            return result.get('id')
        return result

    async def get_table_by_id(self, table_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get table by ID"""
        return await self.get_by_id(table_id, include_deleted)

    async def get_tables_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all tables by workspace"""
        return await self.repository.get_by_workspace(workspace_id)

    async def get_tables_by_area(self, area_id: str) -> List[Dict[str, Any]]:
        """Get all tables by area"""
        return await self.repository.get_by_area(area_id)

    async def get_paginated_tables(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        area_id: Optional[str] = None,
        status: Optional[str] = None,
        order_by: str = 'created_at',
        order_direction: str = 'desc',
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated tables"""
        return await self.repository.get_paginated_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            area_id=area_id,
            status=status,
            order_by=order_by,
            order_direction=order_direction,
        )

    async def update_table(self, table_id: str, data: Dict[str, Any]) -> bool:
        """Update table"""
        return await self.update(table_id, data)

    async def soft_delete_table(self, table_id: str) -> bool:
        """Soft delete table"""
        return await self.soft_delete(table_id)

    async def restore_table(self, table_id: str) -> bool:
        """Restore soft-deleted table"""
        return await self.restore(table_id)
