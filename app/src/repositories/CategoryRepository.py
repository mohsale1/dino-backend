"""
CategoryRepository — async SQLAlchemy 2.x repository for the Category model.
Scoped by persona_id only (workspace_id removed from categories table).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Category import Category


class CategoryRepository(BaseRepository):
    """Repository for Category entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Category, db)

    async def create_category(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new category scoped to a persona."""
        instance = Category(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return row_to_dict(instance)

    async def get_paginated_by_persona(
        self,
        persona_id: int,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated active categories scoped to persona, ordered oldest-first."""
        conditions = [
            Category.persona_id == persona_id,
            Category.is_active.is_(True),
        ]

        if is_available is not None:
            conditions.append(Category.is_available == is_available)

        where_clause = and_(*conditions)

        count_stmt = select(func.count()).select_from(Category).where(where_clause)
        total: int = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Category)
            .where(where_clause)
            .order_by(Category.created_at.asc())
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
        category_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return a single active category by id scoped to persona."""
        stmt = select(Category).where(
            and_(
                Category.id == category_id,
                Category.persona_id == persona_id,
                Category.is_active.is_(True),
            )
        )
        row = (await self.db.execute(stmt)).scalars().first()
        return row_to_dict(row) if row is not None else None

    async def update_for_persona(
        self,
        category_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """UPDATE a category scoped to persona. Single round-trip."""
        payload = {**data, "updated_at": datetime.now(timezone.utc)}
        stmt = (
            update(Category)
            .where(
                and_(
                    Category.id == category_id,
                    Category.persona_id == persona_id,
                    Category.is_active.is_(True),
                )
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def soft_delete_for_persona(
        self,
        category_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete a category scoped to persona."""
        return await self.update_for_persona(category_id, persona_id, {"is_active": False})

    async def restore_for_persona(
        self,
        category_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted category scoped to persona."""
        payload = {"is_active": True, "updated_at": datetime.now(timezone.utc)}
        stmt = (
            update(Category)
            .where(
                and_(
                    Category.id == category_id,
                    Category.persona_id == persona_id,
                    Category.is_active.is_(False),
                )
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def name_exists_for_persona(
        self,
        name: str,
        persona_id: int,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Return True if an active category with the same name (case-insensitive) exists."""
        conditions = [
            func.lower(Category.name) == name.lower(),
            Category.persona_id == persona_id,
            Category.is_active.is_(True),
        ]
        if exclude_id is not None:
            conditions.append(Category.id != exclude_id)

        stmt = select(func.count()).select_from(Category).where(and_(*conditions))
        return (await self.db.execute(stmt)).scalar_one() > 0
