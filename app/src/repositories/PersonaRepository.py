"""
PersonaRepository — async SQLAlchemy 2.x repository for the Persona model.
"""

from typing import Any, Dict, List, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Persona import Persona


class PersonaRepository(BaseRepository):
    """Repository for Persona entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Persona, db)

    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active personas for a workspace."""
        return await self.get_all(filters={"workspace_id": workspace_id})

    async def get_paginated_by_workspace(
        self,
        workspace_id: int,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated personas for a workspace."""
        conditions = [Persona.workspace_id == workspace_id]
        if not include_deleted:
            conditions.append(Persona.is_active.is_(True))  # noqa: E712

        count_stmt = select(func.count()).select_from(Persona).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Persona)
            .where(and_(*conditions))
            .order_by(Persona.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages
