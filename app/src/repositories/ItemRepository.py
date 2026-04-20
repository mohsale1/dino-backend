from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Item import Item


class ItemRepository(BaseRepository):
    """Item repository — async SQLAlchemy 2.x."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Item, db)

    # ------------------------------------------------------------------
    # Simple lookups
    # ------------------------------------------------------------------

    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Return all active (non-deleted) items for a workspace."""
        return await self.get_all(filters={"workspace_id": workspace_id})

    async def get_by_category(self, category_id: str) -> List[Dict[str, Any]]:
        """Return all active (non-deleted) items for a category."""
        return await self.get_all(filters={"category_id": category_id})

    # ------------------------------------------------------------------
    # Paginated query
    # ------------------------------------------------------------------

    async def get_paginated_by_workspace(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        category_id: Optional[str] = None,
        is_available: Optional[bool] = None,
        is_vegetarian: Optional[bool] = None,
        search_query: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Paginated items scoped to a workspace.

        All filtering — including full-text ILIKE search — is pushed down to
        PostgreSQL.  No in-memory filtering is performed.

        Parameters
        ----------
        workspace_id:
            Required scope filter.
        category_id:
            Optional equality filter on category_id.
        is_available:
            Optional boolean filter on is_available.
        is_vegetarian:
            Optional boolean filter on is_vegetarian.
        search_query:
            When provided, adds a SQL ILIKE predicate across name and
            description columns using OR.
        order_by / order_direction:
            Column name and direction ('asc' | 'desc') for ORDER BY.

        Returns
        -------
        (items, total_count, total_pages)
        """
        # --- Build WHERE clauses ---
        # is_active == True is the soft-delete guard (replaces is_deleted == False)
        clauses: list = [
            Item.workspace_id == workspace_id,
            Item.is_active == True,  # noqa: E712
        ]

        if category_id is not None:
            clauses.append(Item.category_id == category_id)

        if is_available is not None:
            clauses.append(Item.is_available == is_available)

        if is_vegetarian is not None:
            clauses.append(Item.is_vegetarian == is_vegetarian)

        if search_query:
            pattern = f"%{search_query}%"
            clauses.append(
                or_(
                    Item.name.ilike(pattern),
                    Item.description.ilike(pattern),
                )
            )

        where_expr = and_(*clauses)

        # --- COUNT query ---
        count_stmt = (
            select(func.count())
            .select_from(Item)
            .where(where_expr)
        )
        total: int = (await self.db.execute(count_stmt)).scalar_one()
        total_pages = max(1, (total + page_size - 1) // page_size)

        # --- DATA query ---
        order_expr = self._order_column(order_by, order_direction)
        data_stmt = select(Item).where(where_expr)
        if order_expr is not None:
            data_stmt = data_stmt.order_by(order_expr)
        data_stmt = data_stmt.limit(page_size).offset((page - 1) * page_size)

        result = await self.db.execute(data_stmt)
        items = [row_to_dict(row) for row in result.scalars().all()]

        return items, total, total_pages
