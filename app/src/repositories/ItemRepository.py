"""
ItemRepository — async SQLAlchemy 2.x repository for the Item model.
Scoped by persona_id. No Category join needed for isolation.
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

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new item and return the full row dict."""
        instance = Item(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return row_to_dict(instance)

    async def update_for_persona(
        self,
        item_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """UPDATE an active item scoped to persona. Single round-trip."""
        payload = {**data, "updated_at": datetime.now(timezone.utc)}
        stmt = (
            update(Item)
            .where(
                and_(
                    Item.id == item_id,
                    Item.persona_id == persona_id,
                    Item.is_active.is_(True),
                )
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def soft_delete_for_persona(
        self,
        item_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete an active item scoped to persona."""
        return await self.update_for_persona(item_id, persona_id, {"is_active": False})

    async def restore_for_persona(
        self,
        item_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted item scoped to persona."""
        payload = {"is_active": True, "updated_at": datetime.now(timezone.utc)}
        stmt = (
            update(Item)
            .where(
                and_(
                    Item.id == item_id,
                    Item.persona_id == persona_id,
                    Item.is_active.is_(False),
                )
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_paginated_by_persona(
        self,
        persona_id: int,
        page: int = 1,
        page_size: int = 20,
        category_id: Optional[int] = None,
        is_available: Optional[bool] = None,
        is_vegetarian: Optional[bool] = None,
        search_query: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated active items scoped to persona, ordered oldest-first."""
        conditions = [
            Item.persona_id == persona_id,
            Item.is_active.is_(True),
        ]

        if category_id is not None:
            conditions.append(Item.category_id == category_id)
        if is_available is not None:
            conditions.append(Item.is_available == is_available)
        if is_vegetarian is not None:
            conditions.append(Item.is_vegetarian == is_vegetarian)
        if search_query:
            pattern = f"%{search_query.strip()}%"
            conditions.append(
                or_(Item.name.ilike(pattern), Item.description.ilike(pattern))
            )

        where_expr = and_(*conditions)

        count_stmt = select(func.count()).select_from(Item).where(where_expr)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Item)
            .where(where_expr)
            .order_by(Item.created_at.asc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()

        result = []
        for idx, row in enumerate(rows, start=offset + 1):
            d = row_to_dict(row)
            d["index"] = idx
            result.append(d)

        return result, total, total_pages

    async def get_by_id_for_persona(
        self,
        item_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return a single active item by id scoped to persona."""
        stmt = select(Item).where(
            and_(
                Item.id == item_id,
                Item.persona_id == persona_id,
                Item.is_active.is_(True),
            )
        )
        row = (await self.db.execute(stmt)).scalars().one_or_none()
        return row_to_dict(row) if row is not None else None

    async def name_exists_for_persona(
        self,
        name: str,
        persona_id: int,
        category_id: int,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """
        Return True if an active item with the same name (case-insensitive)
        exists in the same persona + category. Pass exclude_id on update.
        """
        conditions = [
            func.lower(Item.name) == name.lower(),
            Item.persona_id == persona_id,
            Item.category_id == category_id,
            Item.is_active.is_(True),
        ]
        if exclude_id is not None:
            conditions.append(Item.id != exclude_id)

        stmt = select(func.count()).select_from(Item).where(and_(*conditions))
        return (await self.db.execute(stmt)).scalar_one() > 0

    async def category_belongs_to_persona(
        self,
        category_id: int,
        persona_id: int,
    ) -> bool:
        """Return True if the category is active and belongs to this persona."""
        stmt = select(func.count()).select_from(Category).where(
            and_(
                Category.id == category_id,
                Category.persona_id == persona_id,
                Category.is_active.is_(True),
            )
        )
        return (await self.db.execute(stmt)).scalar_one() > 0
