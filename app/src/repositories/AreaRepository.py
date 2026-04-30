"""
AreaRepository â€” async SQLAlchemy 2.x repository for the Area model.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Area import Area
from src.models.Workspace import workspace_personas


class AreaRepository(BaseRepository):
    """Repository for Area entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Area, db)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _persona_belongs_to_workspace(
        self, workspace_id: int, persona_id: int
    ) -> bool:
        """Return True if the persona is linked to the workspace."""
        stmt = (
            select(func.count())
            .select_from(workspace_personas)
            .where(
                and_(
                    workspace_personas.c.workspace_id == workspace_id,
                    workspace_personas.c.persona_id == persona_id,
                )
            )
        )
        count = (await self.db.execute(stmt)).scalar_one()
        return count > 0

    async def _ensure_workspace_persona(
        self, workspace_id: int, persona_id: int
    ) -> None:
        """Insert into workspace_personas if the link does not already exist."""
        exists = await self._persona_belongs_to_workspace(workspace_id, persona_id)
        if not exists:
            stmt = insert(workspace_personas).values(
                workspace_id=workspace_id,
                persona_id=persona_id,
            )
            await self.db.execute(stmt)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_area(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate persona â†’ workspace membership, ensure workspace_personas link,
        then INSERT the area. All within the same transaction.
        """
        workspace_id: int = data["workspace_id"]
        persona_id: int = data["persona_id"]

        await self._ensure_workspace_persona(workspace_id, persona_id)

        instance = Area(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return row_to_dict(instance)

    async def update_for_workspace(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """
        UPDATE active area scoped to workspace + persona in a single round-trip.
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
                    Area.workspace_id == workspace_id,
                    Area.persona_id == persona_id,
                    Area.is_active.is_(True),
                )
            )
            .values(**payload)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def soft_delete_for_workspace(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
        updated_by: Optional[int] = None,
    ) -> bool:
        """Soft-delete an active area by setting is_active=False."""
        data: Dict[str, Any] = {"is_active": False}
        if updated_by is not None:
            data["updated_by"] = updated_by
        return await self.update_for_workspace(
            area_id=area_id,
            workspace_id=workspace_id,
            persona_id=persona_id,
            data=data,
        )

    async def restore_for_workspace(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """
        Restore a soft-deleted area (is_active=False â†’ True) in a single round-trip.
        Returns True when a row was affected.
        """
        stmt = (
            update(Area)
            .where(
                and_(
                    Area.id == area_id,
                    Area.workspace_id == workspace_id,
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
        workspace_id: int,
        persona_id: int,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Return paginated active areas scoped to workspace + persona, ordered
        oldest-first. Each dict includes a 1-based `index` field that reflects
        the absolute position across all pages.
        """
        conditions = [
            Area.workspace_id == workspace_id,
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
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return a single active area scoped to workspace + persona, or None."""
        stmt = select(Area).where(
            and_(
                Area.id == area_id,
                Area.workspace_id == workspace_id,
                Area.persona_id == persona_id,
                Area.is_active.is_(True),
            )
        )
        row = (await self.db.execute(stmt)).scalars().first()
        return row_to_dict(row) if row is not None else None

    # kept for backward-compat with other callers
    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active areas for a workspace."""
        return await self.get_all(filters={"workspace_id": workspace_id})
