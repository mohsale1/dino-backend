"""
AreaRepository — async SQLAlchemy 2.x repository for the Area model.
Scoped by persona_id only (workspace_id removed from areas table).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Area import Area


class AreaRepository(BaseRepository):
    """Repository for Area entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Area, db)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_area(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new area scoped to a persona."""
        instance = Area(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return row_to_dict(instance)

    async def update_for_persona(
        self,
        area_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """
        UPDATE active area scoped to persona in a single round-trip.
        Stamps updated_at automatically. Returns True when a row was affected.
        """
        payload = {
            **data,
            "updated_at": datetime.now(timezone.utc),
        }
        stmt = (
            update(Area)
            .where(
                and_(
                    Area.id == area_id,
                    Area.persona_id == persona_id,
                    Area.is_active.is_(True),
                )
            )
            .values(**payload)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def soft_delete_for_persona(
        self,
        area_id: int,
        persona_id: int,
        updated_by: Optional[int] = None,
    ) -> bool:
        """Soft-delete an active area by setting is_active=False."""
        return await self.update_for_persona(area_id, persona_id, {"is_active": False})


    async def restore_for_persona(
        self,
        area_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted area (is_active=False → True)."""
        stmt = (
            update(Area)
            .where(
                and_(
                    Area.id == area_id,
                    Area.persona_id == persona_id,
                    Area.is_active.is_(False),
                )
            )
            .values(
                is_active=True,
                updated_at=datetime.now(timezone.utc),
            )
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_all_by_persona(
        self,
        persona_id: int,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Return paginated active areas scoped to persona, ordered oldest-first.
        Each dict includes a 1-based absolute `index` field.
        """
        conditions = [
            Area.persona_id == persona_id,
            Area.is_active.is_(True),
        ]

        if is_available is not None:
            conditions.append(Area.is_available == is_available)

        count_stmt = select(func.count()).select_from(Area).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Area)
            .where(and_(*conditions))
            .order_by(Area.created_at.asc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()

        result = []
        for idx, row in enumerate(rows, start=offset + 1):
            d = row_to_dict(row)
            d["index"] = idx
            result.append(d)

        return result, total, total_pages

    async def get_by_id_for_persona(
        self,
        area_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return a single active area scoped to persona, or None."""
        stmt = select(Area).where(
            and_(
                Area.id == area_id,
                Area.persona_id == persona_id,
                Area.is_active.is_(True),
            )
        )
        row = (await self.db.execute(stmt)).scalars().first()
        return row_to_dict(row) if row is not None else None

    async def name_exists_for_persona(
        self,
        name: str,
        persona_id: int,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """
        Return True if an active area with the same name (case-insensitive)
        already exists for this persona. Pass exclude_id to skip the current
        record when checking during an update.
        """
        conditions = [
            func.lower(Area.name) == name.lower(),
            Area.persona_id == persona_id,
            Area.is_active.is_(True),
        ]
        if exclude_id is not None:
            conditions.append(Area.id != exclude_id)

        stmt = select(func.count()).select_from(Area).where(and_(*conditions))
        count = (await self.db.execute(stmt)).scalar_one()
        return count > 0
