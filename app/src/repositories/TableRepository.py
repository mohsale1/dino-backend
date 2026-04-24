"""
TableRepository — async SQLAlchemy 2.x repository for the Table model.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Table import Table


class TableRepository(BaseRepository):
    """Repository for Table entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Table, db)

    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active tables for a workspace."""
        return await self.get_all(filters={"workspace_id": workspace_id})

    async def get_by_area(self, area_id: int) -> List[Dict[str, Any]]:
        """Return all active tables in an area."""
        return await self.get_all(filters={"area_id": area_id})

    async def get_paginated_by_workspace(
        self,
        workspace_id: int,
        area_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated tables for a workspace with optional filters."""
        conditions = [Table.workspace_id == workspace_id, Table.is_active.is_(True)]

        if area_id is not None:
            conditions.append(Table.area_id == area_id)
        if status is not None:
            conditions.append(Table.status == status)

        count_stmt = select(func.count()).select_from(Table).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Table)
            .where(and_(*conditions))
            .order_by(Table.display_order.asc(), Table.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages

    async def get_status_counts(self, workspace_id: int) -> Dict[str, int]:
        """Return counts of tables grouped by status for a workspace."""
        stmt = select(
            func.count(case((Table.status == "available", 1))).label("available"),
            func.count(case((Table.status == "occupied", 1))).label("occupied"),
            func.count(case((Table.status == "reserved", 1))).label("reserved"),
            func.count(case((Table.is_active.is_(False), 1))).label("inactive")
        ).where(Table.workspace_id == workspace_id)

        row = (await self.db.execute(stmt)).one_or_none()
        if row is None:
            return {"available": 0, "occupied": 0, "reserved": 0, "inactive": 0}
        return {
            "available": row.available,
            "occupied": row.occupied,
            "reserved": row.reserved,
            "inactive": row.inactive,
        }
