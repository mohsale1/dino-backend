"""
PersonaRepository — async SQLAlchemy 2.x repository for the Persona model.
workspace_id removed from personas table — association via workspace_personas.
"""

from typing import Any, Dict, List, Optional, Tuple

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
            .order_by(Persona.created_at.asc())
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

    async def update_for_workspace(
        self,
        persona_id: int,
        workspace_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """
        UPDATE a persona scoped to workspace via workspace_personas join.
        Single round-trip — no pre-fetch needed.
        """
        from datetime import datetime, timezone
        from sqlalchemy import update as sa_update

        payload = {**data, "updated_at": datetime.now(timezone.utc)}

        # Verify persona belongs to workspace via subquery
        subq = (
            select(workspace_personas.c.persona_id)
            .where(
                workspace_personas.c.workspace_id == workspace_id,
                workspace_personas.c.persona_id == persona_id,
            )
            .scalar_subquery()
        )
        stmt = (
            sa_update(Persona)
            .where(
                Persona.id == subq,
                Persona.is_active.is_(True),
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def name_exists_for_workspace(
        self,
        name: str,
        workspace_id: int,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Return True if an active persona with the same name exists in this workspace."""
        conditions = [
            func.lower(Persona.name) == name.lower(),
            workspace_personas.c.workspace_id == workspace_id,
            Persona.is_active.is_(True),
        ]
        if exclude_id is not None:
            conditions.append(Persona.id != exclude_id)

        stmt = (
            select(func.count())
            .select_from(Persona)
            .join(workspace_personas, workspace_personas.c.persona_id == Persona.id)
            .where(and_(*conditions))
        )
        return (await self.db.execute(stmt)).scalar_one() > 0

