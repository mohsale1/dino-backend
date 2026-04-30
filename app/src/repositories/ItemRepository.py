"""
ItemRepository — async SQLAlchemy 2.x repository for the Item model.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Category import Category
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
        persona_id: int,
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[int] = None,
        is_available: Optional[bool] = None,
        is_vegetarian: Optional[bool] = None,
        search_query: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated items for a workspace scoped to a persona, with optional filters."""
        conditions = [
            Item.workspace_id == workspace_id,
            Item.is_active.is_(True),
            Category.persona_id == persona_id,
        ]

        if category_id is not None:
            conditions.append(Item.category_id == category_id)
        if is_available is not None:
            conditions.append(Item.is_available == is_available)
        if is_vegetarian is not None:
            conditions.append(Item.is_vegetarian == is_vegetarian)
        if search_query:
            pattern = f"%{search_query}%"
            conditions.append(
                or_(Item.name.ilike(pattern), Item.description.ilike(pattern))
            )

        where_expr = and_(*conditions)

        count_stmt = (
            select(func.count())
            .select_from(Item)
            .join(Category, Item.category_id == Category.id)
            .where(where_expr)
        )
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Item)
            .join(Category, Item.category_id == Category.id)
            .where(where_expr)
            .order_by(Item.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages

    async def get_by_id_for_persona(
        self,
        item_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return a single active item by id, scoped to a persona via Category join."""
        stmt = (
            select(Item)
            .join(Category, Item.category_id == Category.id)
            .where(
                Item.id == item_id,
                Item.workspace_id == workspace_id,
                Item.is_active.is_(True),
                Category.persona_id == persona_id,
            )
        )
        row = (await self.db.execute(stmt)).scalars().one_or_none()
        return row_to_dict(row) if row is not None else None

    async def update_for_persona(
        self,
        item_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """
        Update an active item that belongs to the given persona (via Category join).
        Uses a correlated subquery so the entire operation is a single DB round-trip.
        Does NOT call self.db.commit() — commit is managed by get_db.
        """
        payload = {**data, "updated_at": datetime.now(timezone.utc)}

        subq = (
            select(Item.id)
            .join(Category, Item.category_id == Category.id)
            .where(
                Item.id == item_id,
                Item.workspace_id == workspace_id,
                Category.persona_id == persona_id,
                Item.is_active.is_(True),
            )
            .scalar_subquery()
        )
        stmt = (
            update(Item)
            .where(Item.id == subq)
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def soft_delete_for_persona(
        self,
        item_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete an active item scoped to a persona by setting is_active=False."""
        return await self.update_for_persona(
            item_id=item_id,
            workspace_id=workspace_id,
            persona_id=persona_id,
            data={"is_active": False},
        )

    async def restore_for_persona(
        self,
        item_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """
        Restore a soft-deleted item that belongs to the given persona (via Category join).
        Matches only rows where is_active=False.
        Does NOT call self.db.commit() — commit is managed by get_db.
        """
        payload = {
            "is_active": True,
            "updated_at": datetime.now(timezone.utc),
        }

        subq = (
            select(Item.id)
            .join(Category, Item.category_id == Category.id)
            .where(
                Item.id == item_id,
                Item.workspace_id == workspace_id,
                Category.persona_id == persona_id,
                Item.is_active.is_(False),
            )
            .scalar_subquery()
        )
        stmt = (
            update(Item)
            .where(Item.id == subq)
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0