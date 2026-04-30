"""
AreaService â€” business logic for dining areas.
"""

from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.AreaRepository import AreaRepository


class AreaService(BaseService):
    """Service for managing dining areas."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.area_repo = AreaRepository(db)
        super().__init__(self.area_repo)

    async def create_area(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new area.
        - Validates persona_id is provided.
        - Ensures workspace_personas link exists (creates it if not).
        - Inserts the area row.
        """
        if not data.get("persona_id"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="persona_id is required to create an area",
            )
        data.setdefault("is_active", True)
        return await self.area_repo.create_area(data)

    async def get_all_areas(
        self,
        workspace_id: int,
        persona_id: int,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated active areas scoped to workspace and persona, with 1-based absolute index."""
        return await self.area_repo.get_all_by_persona(
            workspace_id=workspace_id,
            persona_id=persona_id,
            is_available=is_available,
            page=page,
            page_size=page_size,
        )


    async def get_area_for_persona(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single area scoped to workspace and persona."""
        return await self.area_repo.get_by_id_for_persona(
            area_id, workspace_id, persona_id
        )

    async def update_area(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Update an area scoped to workspace and persona."""
        return await self.area_repo.update_for_workspace(
            area_id, workspace_id, persona_id, data
        )

    async def soft_delete_area(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
        updated_by: Optional[int] = None,
    ) -> bool:
        """Soft-delete an area scoped to workspace and persona."""
        return await self.area_repo.soft_delete_for_workspace(
            area_id, workspace_id, persona_id, updated_by=updated_by
        )

    async def restore_area(
        self,
        area_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted area scoped to workspace and persona."""
        return await self.area_repo.restore_for_workspace(
            area_id, workspace_id, persona_id
        )
