"""
PersonaService — persona management for dino-system.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.models.Workspace import workspace_personas
from src.repositories.PersonaRepository import PersonaRepository


class PersonaService(BaseService):
    """Service for persona management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._persona_repo = PersonaRepository(db)
        super().__init__(self._persona_repo)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_persona(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create persona and link to workspace via workspace_personas."""
        workspace_id = data.pop("workspace_id", None)
        result = await self.create(data)
        persona_id = result.get("id")

        if workspace_id and persona_id:
            stmt = (
                pg_insert(workspace_personas)
                .values(workspace_id=workspace_id, persona_id=persona_id)
                .on_conflict_do_nothing()
            )
            await self.db.execute(stmt)
            await self.db.flush()

        return result

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_paginated_personas(
        self,
        workspace_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated personas with optional workspace filter."""
        if workspace_id is not None:
            return await self._persona_repo.get_paginated_by_workspace(
                workspace_id=workspace_id,
                page=page,
                page_size=page_size,
                include_deleted=include_deleted,
            )
        return await self.get_paginated(
            page=page,
            page_size=page_size,
            include_deleted=include_deleted,
        )

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_persona(self, persona_id: int, data: Dict[str, Any]) -> bool:
        return await self.update(persona_id, data)

    async def soft_delete_persona(self, persona_id: int) -> bool:
        return await self.soft_delete(persona_id)

    async def restore_persona(self, persona_id: int) -> bool:
        return await self.restore(persona_id)

    async def toggle_open(self, persona_id: int, is_open: bool) -> bool:
        return await self.update(persona_id, {"is_open": is_open})

    async def deactivate_persona(self, persona_id: int) -> bool:
        """Billing suspension: set is_deactivated=True."""
        return await self.update(persona_id, {"is_deactivated": True})

    async def reactivate_persona(self, persona_id: int) -> bool:
        """Lift billing suspension: set is_deactivated=False."""
        return await self.update(persona_id, {"is_deactivated": False})
