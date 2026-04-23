"""
PersonaService — business logic for personas (outlet/branch profiles).
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.models.Workspace import workspace_personas
from src.repositories.PersonaRepository import PersonaRepository


class PersonaService(BaseService):
    """Service for managing personas."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.persona_repo = PersonaRepository(db)
        super().__init__(self.persona_repo)

    async def create_persona(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a persona and link it to the workspace via workspace_personas.
        Expects data to contain workspace_id.
        """
        data.setdefault("is_active", True)
        workspace_id = data.get("workspace_id")

        created = await self.persona_repo.create(data)
        persona_id = created["id"]

        if workspace_id:
            stmt = (
                pg_insert(workspace_personas)
                .values(workspace_id=workspace_id, persona_id=persona_id)
                .on_conflict_do_nothing()
            )
            await self.db.execute(stmt)

        return created

    async def get_paginated_personas(
        self,
        workspace_id: int,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated personas for a workspace."""
        return await self.persona_repo.get_paginated_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            include_deleted=include_deleted,
        )

    async def update_persona(self, persona_id: int, data: Dict[str, Any]) -> bool:
        """Update a persona by ID."""
        return await self.persona_repo.update(persona_id, data)

    async def toggle_open(self, persona_id: int, is_open: bool) -> bool:
        """Toggle the is_open flag on a persona."""
        return await self.persona_repo.update(persona_id, {"is_open": is_open})

    async def soft_delete_persona(self, persona_id: int) -> bool:
        """Soft-delete a persona."""
        return await self.persona_repo.soft_delete(persona_id)

    async def restore_persona(self, persona_id: int) -> bool:
        """Restore a soft-deleted persona."""
        return await self.persona_repo.restore(persona_id)
