"""
WorkspaceRepository — async SQLAlchemy 2.x repository for the Workspace model.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Workspace import Workspace


class WorkspaceRepository(BaseRepository):
    """Repository for Workspace entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Workspace, db)

    async def get_by_owner(self, owner_id: int) -> List[Dict[str, Any]]:
        """Return all active workspaces owned by a user."""
        return await self.get_all(filters={"owner_id": owner_id})

    async def get_with_billing(self, workspace_id: int) -> Optional[Dict[str, Any]]:
        """Return workspace dict (billing is loaded separately via BillingService)."""
        return await self.get_by_id(workspace_id)

    async def get_paginated_workspaces(
        self,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated workspaces with optional is_active filter."""
        conditions = []

        if is_active is not None:
            conditions.append(Workspace.is_active == is_active)
        else:
            # Default: only active workspaces
            conditions.append(Workspace.is_active == True)  # noqa: E712

        where_expr = and_(*conditions) if conditions else None

        count_stmt = select(func.count()).select_from(Workspace)
        if where_expr is not None:
            count_stmt = count_stmt.where(where_expr)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = select(Workspace)
        if where_expr is not None:
            data_stmt = data_stmt.where(where_expr)
        data_stmt = (
            data_stmt.order_by(Workspace.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages
