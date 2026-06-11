"""
PersonaRepository — async SQLAlchemy 2.x repository for the Persona model.
workspace_id removed from personas table — association via workspace_personas.
"""

from typing import Any, Dict, List, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Persona import Persona
from src.models.Workspace import workspace_personas


class PersonaRepository(BaseRepository):
    """Repository for Persona entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Persona, db)

    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active personas linked to a workspace via workspace_personas."""
        stmt = (
            select(Persona)
            .join(workspace_personas, workspace_personas.c.persona_id == Persona.id)
            .where(
                workspace_personas.c.workspace_id == workspace_id,
                Persona.is_active.is_(True),
            )
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [row_to_dict(r) for r in rows]

    async def get_paginated_by_workspace(
        self,
        workspace_id: int,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated personas linked to a workspace via workspace_personas."""
        conditions = [workspace_personas.c.workspace_id == workspace_id]
        if not include_deleted:
            conditions.append(Persona.is_active.is_(True))

        base_stmt = (
            select(Persona)
            .join(workspace_personas, workspace_personas.c.persona_id == Persona.id)
            .where(and_(*conditions))
        )

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            base_stmt
            .order_by(Persona.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages
