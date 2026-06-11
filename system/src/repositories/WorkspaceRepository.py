"""
WorkspaceRepository — async SQLAlchemy 2.x repository for the Workspace model.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Workspace import Workspace
from src.models.WorkspaceBilling import WorkspaceBilling


class WorkspaceRepository(BaseRepository):
    """Repository for Workspace entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Workspace, db)

    async def get_paginated_workspaces(
        self,
        is_active: Optional[bool] = None,
        plan: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Return (items, total_count, total_pages) with optional filtering.

        Joins workspace_billing for plan filter when plan is provided.
        """
        conditions = []

        if is_active is not None:
            conditions.append(Workspace.is_active == is_active)
        else:
            conditions.append(Workspace.is_active == True)  # noqa: E712

        if plan is not None:
            # Join workspace_billing to filter by plan
            count_stmt = (
                select(func.count())
                .select_from(Workspace)
                .join(WorkspaceBilling, WorkspaceBilling.workspace_id == Workspace.id)
                .where(and_(*conditions))
                .where(WorkspaceBilling.plan == plan)
            )
            total = (await self.db.execute(count_stmt)).scalar_one() or 0
            total_pages = max(1, (total + page_size - 1) // page_size)

            offset = (page - 1) * page_size
            data_stmt = (
                select(Workspace)
                .join(WorkspaceBilling, WorkspaceBilling.workspace_id == Workspace.id)
                .where(and_(*conditions))
                .where(WorkspaceBilling.plan == plan)
                .order_by(Workspace.created_at.desc())
                .limit(page_size)
                .offset(offset)
            )
            rows = (await self.db.execute(data_stmt)).scalars().all()
            return [row_to_dict(r) for r in rows], total, total_pages

        # No plan filter — use base paginated.
        # When is_active is None, default to showing only active workspaces.
        effective_is_active = is_active if is_active is not None else True
        return await self.get_paginated(
            page=page,
            page_size=page_size,
            filters={"is_active": effective_is_active},
            include_deleted=not effective_is_active,
            order_by="created_at",
            order_direction="desc",
        )
