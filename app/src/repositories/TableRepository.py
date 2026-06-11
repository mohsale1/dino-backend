"""
TableRepository — async SQLAlchemy 2.x repository for the Table model.
Scoped by persona_id only (workspace_id removed from tables table).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Table import Table


class TableRepository(BaseRepository):
    """Repository for Table entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Table, db)

    async def create_table(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new table and return the full row dict."""
        instance = Table(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return row_to_dict(instance)

    async def table_number_exists_for_persona(
        self,
        table_number: str,
        persona_id: int,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Return True if an active table with the same number exists for this persona."""
        conditions = [
            Table.table_number == table_number,
            Table.persona_id == persona_id,
            Table.is_active.is_(True),
        ]
        if exclude_id is not None:
            conditions.append(Table.id != exclude_id)
        stmt = select(func.count()).select_from(Table).where(and_(*conditions))
        return (await self.db.execute(stmt)).scalar_one() > 0

    async def get_paginated_by_persona(
        self,
        persona_id: int,
        area_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated active tables scoped to persona, with optional filters."""
        conditions = [
            Table.persona_id == persona_id,
            Table.is_active.is_(True),
        ]

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
            .order_by(Table.table_number.asc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        result = []
        for index, row in enumerate(rows, start=offset + 1):
            d = row_to_dict(row)
            d["index"] = index
            result.append(d)
        return result, total, total_pages

    async def get_by_id_for_persona(
        self,
        table_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return a single active table by id scoped to persona."""
        stmt = select(Table).where(
            and_(
                Table.id == table_id,
                Table.persona_id == persona_id,
                Table.is_active.is_(True),
            )
        )
        row = (await self.db.execute(stmt)).scalars().one_or_none()
        return row_to_dict(row) if row is not None else None

    async def update_for_persona(
        self,
        table_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Update an active table scoped to persona. Single round-trip."""
        payload = {**data, "updated_at": datetime.now(timezone.utc)}
        stmt = (
            update(Table)
            .where(
                and_(
                    Table.id == table_id,
                    Table.persona_id == persona_id,
                    Table.is_active.is_(True),
                )
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def soft_delete_for_persona(
        self,
        table_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete an active table scoped to persona."""
        return await self.update_for_persona(table_id, persona_id, {"is_active": False})

    async def restore_for_persona(
        self,
        table_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted table scoped to persona."""
        payload = {
            "is_active": True,
            "updated_at": datetime.now(timezone.utc),
        }
        stmt = (
            update(Table)
            .where(
                and_(
                    Table.id == table_id,
                    Table.persona_id == persona_id,
                    Table.is_active.is_(False),
                )
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def get_status_counts(
        self,
        persona_id: int,
    ) -> Dict[str, int]:
        """Return counts of tables grouped by status scoped to persona."""
        stmt = (
            select(
                func.count(case((Table.status == "available", 1))).label("available"),
                func.count(case((Table.status == "occupied", 1))).label("occupied"),
                func.count(case((Table.status == "reserved", 1))).label("reserved"),
                func.count(case((Table.is_active.is_(False), 1))).label("inactive"),
            )
            .select_from(Table)
            .where(Table.persona_id == persona_id)
        )
        row = (await self.db.execute(stmt)).one_or_none()
        if row is None:
            return {"available": 0, "occupied": 0, "reserved": 0, "inactive": 0}
        return {
            "available": row.available,
            "occupied": row.occupied,
            "reserved": row.reserved,
            "inactive": row.inactive,
        }
