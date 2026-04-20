"""
WorkspaceRepository — async SQLAlchemy 2.x repository for the Workspace model.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseRepository import BaseRepository
from src.models.Workspace import Workspace


class WorkspaceRepository(BaseRepository):
    """Repository for Workspace entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Workspace, db)

    async def get_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        """Return all non-deleted workspaces owned by the given user."""
        return await self.get_all(filters={"owner_id": owner_id})

    async def get_paginated_workspaces(
        self,
        page: int = 1,
        page_size: int = 10,
        is_active: Optional[bool] = None,
        subscription_plan: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Return (items, total_count) with optional filtering and pagination.

        Filters
        -------
        is_active         – match the is_active column when provided.
        subscription_plan – match the subscription_plan column when provided.
        """
        filters: Dict[str, Any] = {}

        if is_active is not None:
            filters["is_active"] = is_active
        if subscription_plan is not None:
            filters["subscription_plan"] = subscription_plan

        return await self.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=order_by,
            order_direction=order_direction,
        )
