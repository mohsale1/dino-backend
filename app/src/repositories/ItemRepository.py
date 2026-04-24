"""
ItemRepository — async SQLAlchemy 2.x repository for the Item model.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Item import Item


class ItemRepository(BaseRepository):
    """Repository for Item entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Item, db)

    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active items for a workspace."""
        return await self.get_all(filters={"workspace_id": workspace_id})

    async def get_by_category(self, category_id: int) -> List[Dict[str, Any]]:
        """Return all active items for a category."""
        return await self.get_all(filters={"category_id": category_id})

    async def get_paginated_by_workspace(
        self,
        workspace_id: int,
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[int] = None,
        is_available: Optional[bool] = None,
        is_vegetarian: Optional[bool] = None,
        search_query: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated items for a workspace with optional filters."""
        clauses = [Item.workspace_id == workspace_id, Item.is_active.is_(True)]  # noqa: E712

        if category_id is not None:
            clauses.append(Item.category_id == category_id)
        if is_available is not None:
            clauses.append(Item.is_available == is_available)
        if is_vegetarian is not None:
            clauses.append(Item.is_vegetarian == is_vegetarian)
        if search_query:
            pattern = f"%{search_query}%"
            clauses.append(
                or_(Item.name.ilike(pattern), Item.description.ilike(pattern))
            )

        where_expr = and_(*clauses)

        count_stmt = select(func.count()).select_from(Item).where(where_expr)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Item)
            .where(where_expr)
            .order_by(Item.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages
