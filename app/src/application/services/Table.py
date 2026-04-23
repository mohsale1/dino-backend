"""
TableService — business logic for restaurant tables.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.TableRepository import TableRepository


class TableService(BaseService):
    """Service for managing restaurant tables."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.table_repo = TableRepository(db)
        super().__init__(self.table_repo)

    async def create_table(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new table."""
        data.setdefault("is_active", True)
        data.setdefault("status", "available")
        return await self.table_repo.create(data)

    async def get_paginated_tables(
        self,
        workspace_id: int,
        area_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated tables with optional filters."""
        return await self.table_repo.get_paginated_by_workspace(
            workspace_id=workspace_id,
            area_id=area_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    async def update_table(self, table_id: int, data: Dict[str, Any]) -> bool:
        """Update a table by ID."""
        return await self.table_repo.update(table_id, data)

    async def update_table_status(self, table_id: int, status: str) -> bool:
        """Update only the status field of a table."""
        return await self.table_repo.update(table_id, {"status": status})

    async def soft_delete_table(self, table_id: int) -> bool:
        """Soft-delete a table."""
        return await self.table_repo.soft_delete(table_id)

    async def restore_table(self, table_id: int) -> bool:
        """Restore a soft-deleted table."""
        return await self.table_repo.restore(table_id)

    async def get_table_status_summary(self, workspace_id: int) -> Dict[str, int]:
        """Return counts of tables grouped by status."""
        return await self.table_repo.get_status_counts(workspace_id)
