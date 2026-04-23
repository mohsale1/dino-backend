"""
WorkspaceService — workspace management including billing and persona associations.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.base.BaseModel import row_to_dict
from src.models.Workspace import Workspace, workspace_personas
from src.models.WorkspaceBilling import WorkspaceBilling
from src.repositories.PersonaRepository import PersonaRepository
from src.repositories.WorkspaceRepository import WorkspaceRepository


class WorkspaceService(BaseService):
    """Service for workspace management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._ws_repo = WorkspaceRepository(db)
        super().__init__(self._ws_repo)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_workspace(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create workspace, create workspace_billing record, link persona_ids."""
        persona_ids = data.pop("persona_ids", None) or []

        result = await self.create(data)
        workspace_id = result.get("id")

        # Create workspace_billing with plan=free
        billing = WorkspaceBilling(workspace_id=workspace_id, plan="free", plan_status="active")
        self.db.add(billing)
        await self.db.flush()

        # Link personas
        for pid in persona_ids:
            await self.add_persona(workspace_id, pid)

        return result

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_workspace_details(self, workspace_id: int) -> Optional[Dict[str, Any]]:
        """Return workspace with billing and personas resolved."""
        workspace = await self.get_by_id(workspace_id)
        if not workspace:
            return None

        # Resolve billing
        billing_stmt = select(WorkspaceBilling).where(
            WorkspaceBilling.workspace_id == workspace_id
        )
        billing_result = await self.db.execute(billing_stmt)
        billing_obj = billing_result.scalars().first()
        workspace["billing"] = row_to_dict(billing_obj) if billing_obj else None

        # Resolve personas via join table
        persona_stmt = select(workspace_personas.c.persona_id).where(
            workspace_personas.c.workspace_id == workspace_id
        )
        persona_result = await self.db.execute(persona_stmt)
        persona_ids = [row[0] for row in persona_result.all()]

        persona_repo = PersonaRepository(self.db)
        personas = []
        for pid in persona_ids:
            persona = await persona_repo.get_by_id(pid)
            if persona:
                personas.append(persona)
        workspace["personas"] = personas
        workspace["persona_ids"] = persona_ids

        return workspace

    async def get_paginated_workspaces(
        self,
        is_active: Optional[bool] = None,
        plan: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated workspaces with optional billing plan filter."""
        return await self._ws_repo.get_paginated_workspaces(
            is_active=is_active,
            plan=plan,
            page=page,
            page_size=page_size,
        )

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_workspace(self, workspace_id: int, data: Dict[str, Any]) -> bool:
        """Update workspace fields; sync persona_ids if provided."""
        persona_ids = data.pop("persona_ids", None)
        success = await self.update(workspace_id, data)

        if success and persona_ids is not None:
            # Clear and re-link
            await self.db.execute(
                delete(workspace_personas).where(
                    workspace_personas.c.workspace_id == workspace_id
                )
            )
            for pid in persona_ids:
                await self.add_persona(workspace_id, pid)

        return success

    # ------------------------------------------------------------------
    # Billing
    # ------------------------------------------------------------------

    async def get_billing(self, workspace_id: int) -> Optional[Dict[str, Any]]:
        """Fetch workspace_billing record."""
        stmt = select(WorkspaceBilling).where(WorkspaceBilling.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        obj = result.scalars().first()
        return row_to_dict(obj) if obj else None

    async def update_billing(self, workspace_id: int, billing_data: Dict[str, Any]) -> bool:
        """Update workspace_billing record."""
        from datetime import datetime, timezone
        stmt = select(WorkspaceBilling).where(WorkspaceBilling.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        obj = result.scalars().first()
        if not obj:
            return False
        for key, value in billing_data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        obj.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    # ------------------------------------------------------------------
    # Persona association management
    # ------------------------------------------------------------------

    async def add_persona(self, workspace_id: int, persona_id: int) -> bool:
        """Link a persona to a workspace (ON CONFLICT DO NOTHING)."""
        stmt = (
            pg_insert(workspace_personas)
            .values(workspace_id=workspace_id, persona_id=persona_id)
            .on_conflict_do_nothing()
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return True

    async def remove_persona(self, workspace_id: int, persona_id: int) -> bool:
        """Unlink a persona from a workspace."""
        stmt = delete(workspace_personas).where(
            workspace_personas.c.workspace_id == workspace_id,
            workspace_personas.c.persona_id == persona_id,
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return True
