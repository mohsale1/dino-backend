"""
Workspace Service — async SQLAlchemy 2.x
Replaces Firestore ArrayUnion/ArrayRemove with join-table operations.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.models.Workspace import Workspace, workspace_personas
from src.repositories.PersonaRepository import PersonaRepository
from src.repositories.UserRepository import UserRepository
from src.repositories.WorkspaceRepository import WorkspaceRepository


class WorkspaceService(BaseService):
    """Service for workspace management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        super().__init__(WorkspaceRepository(db))

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_workspace(self, data: Dict[str, Any]) -> str:
        """Create a workspace and return its ID."""
        # persona_ids is managed via the join table — strip it from the direct insert
        persona_ids = data.pop('persona_ids', None)

        result = await self.create(data)
        workspace_id = result.get("id") if isinstance(result, dict) else result

        # Link personas via join table if provided
        if persona_ids:
            for pid in persona_ids:
                await self.add_persona(workspace_id, pid)

        return workspace_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_workspace_details(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """
        Return workspace with owner and personas resolved.

        owner_id references application_users (cross-service) — fetched
        from the same DB only if the column is populated.
        personas are resolved via the workspace_personas join table.
        """
        workspace = await self.get_by_id(workspace_id)
        if not workspace:
            return None

        # Resolve owner (application_users lives in the same DB for dino-system)
        owner_id = workspace.get("owner_id")
        if owner_id:
            user_repo = UserRepository(self.db)
            owner = await user_repo.get_by_id(owner_id)
            if owner:
                owner.pop("password_hash", None)
                workspace["owner"] = owner

        # Resolve personas via join table
        stmt = select(workspace_personas.c.persona_id).where(
            workspace_personas.c.workspace_id == workspace_id
        )
        result = await self.db.execute(stmt)
        persona_ids = [str(row[0]) for row in result.all()]

        if persona_ids:
            persona_repo = PersonaRepository(self.db)
            personas = []
            for pid in persona_ids:
                persona = await persona_repo.get_by_id(pid)
                if persona:
                    personas.append(persona)
            workspace["personas"] = personas
        else:
            workspace["personas"] = []

        return workspace

    async def get_personas(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Return all personas linked to a workspace."""
        stmt = select(workspace_personas.c.persona_id).where(
            workspace_personas.c.workspace_id == workspace_id
        )
        result = await self.db.execute(stmt)
        persona_ids = [str(row[0]) for row in result.all()]

        persona_repo = PersonaRepository(self.db)
        personas = []
        for pid in persona_ids:
            persona = await persona_repo.get_by_id(pid)
            if persona:
                personas.append(persona)
        return personas

    # ------------------------------------------------------------------
    # Persona association management
    # (replaces Firestore ArrayUnion / ArrayRemove)
    # ------------------------------------------------------------------

    async def add_persona(self, workspace_id: str, persona_id: str) -> bool:
        """
        Link a persona to a workspace via the join table.
        Silently ignores duplicates (ON CONFLICT DO NOTHING).
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = (
            pg_insert(workspace_personas)
            .values(workspace_id=workspace_id, persona_id=persona_id)
            .on_conflict_do_nothing()
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return True

    async def remove_persona(self, workspace_id: str, persona_id: str) -> bool:
        """Unlink a persona from a workspace."""
        stmt = delete(workspace_personas).where(
            workspace_personas.c.workspace_id == workspace_id,
            workspace_personas.c.persona_id == persona_id,
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return True

    # ------------------------------------------------------------------
    # Billing
    # ------------------------------------------------------------------

    async def update_billing_info(self, workspace_id: str, billing_info: Dict[str, Any]) -> bool:
        """Update billing fields on a workspace."""
        return await self.update(workspace_id, billing_info)
