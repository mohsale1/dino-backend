"""
CategoryRepository — async SQLAlchemy 2.x repository for the Category model.
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

    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active categories for a workspace (utility — no persona isolation)."""
        return await self.get_all(filters={"workspace_id": workspace_id})

    async def get_paginated_by_workspace(
        self,
        workspace_id: int,
        persona_id: int,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated categories scoped to workspace + persona with optional filters."""
        conditions = [
            Category.workspace_id == workspace_id,
            Category.persona_id == persona_id,
            Category.is_active.is_(True),
        ]

        if is_available is not None:
            conditions.append(Category.is_available == is_available)

        where_clause = and_(*conditions)

        count_stmt = select(func.count()).select_from(Category).where(where_clause)
        total: int = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        data_stmt = (
            select(Category)
            .where(where_clause)
            .order_by(Category.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages

    async def get_by_id_for_persona(
        self,
        category_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """SELECT a single active category by id + workspace_id + persona_id.

        Returns a dict when found, None otherwise.
        """
        stmt = select(Category).where(
            Category.id == category_id,
            Category.workspace_id == workspace_id,
            Category.persona_id == persona_id,
            Category.is_active.is_(True),
        )
        row = (await self.db.execute(stmt)).scalars().first()
        return row_to_dict(row) if row is not None else None

    async def update_for_workspace(
        self,
        category_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """UPDATE a category scoped to workspace + persona.

        Folds the ownership check into the WHERE clause — single round-trip.
        Returns True when a row was matched and updated.
        """
        payload = {**data, "updated_at": datetime.now(timezone.utc)}
        stmt = (
            update(Category)
            .where(
                Category.id == category_id,
                Category.workspace_id == workspace_id,
                Category.persona_id == persona_id,
                Category.is_active.is_(True),
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def soft_delete_for_workspace(
        self,
        category_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete a category scoped to workspace + persona.

        Single round-trip — no pre-fetch SELECT needed.
        """
        return await self.update_for_workspace(
            category_id,
            workspace_id,
            persona_id,
            {"is_active": False},
        )

    async def restore_for_workspace(
        self,
        category_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted category scoped to workspace + persona.

        Matches only inactive rows — single round-trip, no pre-fetch SELECT needed.
        """
        payload = {"is_active": True, "updated_at": datetime.now(timezone.utc)}
        stmt = (
            update(Category)
            .where(
                Category.id == category_id,
                Category.workspace_id == workspace_id,
                Category.persona_id == persona_id,
                Category.is_active.is_(False),
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0
