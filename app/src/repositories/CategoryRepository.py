"""
CategoryRepository — async SQLAlchemy 2.x repository for the Category model.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Category import Category


class CategoryRepository(BaseRepository):
    """Repository for Category entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Category, db)

    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active categories for a workspace."""
        return await self.get_all(filters={"workspace_id": workspace_id})

    async def get_paginated_by_workspace(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated categories for a workspace with optional filters."""
        conditions = [Category.workspace_id == workspace_id, Category.is_active == True]  # noqa: E712

        if persona_id is not None:
            conditions.append(Category.persona_id == persona_id)
        if is_available is not None:
            conditions.append(Category.is_available == is_available)

        count_stmt = select(func.count()).select_from(Category).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Category)
            .where(and_(*conditions))
            .order_by(Category.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages
