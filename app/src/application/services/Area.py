"""
AreaService — business logic for dining areas.
"""

from typing import Any, Dict, List, Optional, Tuple

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
        """Create a new area."""
        data.setdefault("is_active", True)
        return await self.area_repo.create(data)

    async def get_paginated_areas(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated areas with optional filters."""
        return await self.area_repo.get_paginated_by_workspace(
            workspace_id=workspace_id,
            persona_id=persona_id,
            is_available=is_available,
            page=page,
            page_size=page_size,
        )

    async def update_area(self, area_id: int, data: Dict[str, Any]) -> bool:
        """Update an area by ID."""
        return await self.area_repo.update(area_id, data)

    async def soft_delete_area(self, area_id: int) -> bool:
        """Soft-delete an area."""
        return await self.area_repo.soft_delete(area_id)

    async def restore_area(self, area_id: int) -> bool:
        """Restore a soft-deleted area."""
        return await self.area_repo.restore(area_id)
