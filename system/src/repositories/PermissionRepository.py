"""
PermissionRepository — async SQLAlchemy 2.x repository for the Permission model.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Permission import Permission


class PermissionRepository(BaseRepository):
    """Repository for Permission entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Permission, db)

    # ------------------------------------------------------------------
    # Simple lookups
    # ------------------------------------------------------------------

    async def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Return all active permissions in the given category."""
        return await self.get_all(filters={"category": category})

    async def get_by_resource(self, resource: str) -> List[Dict[str, Any]]:
        """Return all active permissions targeting the given resource."""
        return await self.get_all(filters={"resource": resource})

    # ------------------------------------------------------------------
    # Existence check
    # ------------------------------------------------------------------

    async def permission_exists(
        self,
        category: str,
        resource: str,
        action: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """
        Return True if a permission with the given (category, resource, action) exists.
        Optionally exclude a specific record (useful for update validation).
        """
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.category == category)
            .where(self.model.resource == resource)
            .where(self.model.action == action)
        )
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        result = await self.db.execute(stmt)
        return (result.scalar_one() or 0) > 0

    # ------------------------------------------------------------------
    # Paginated filtered query
    # ------------------------------------------------------------------

    async def get_paginated_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        is_active: Optional[bool] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return (items, total_count, total_pages) with optional filtering."""
        conditions = []

        if is_active is None:
            conditions.append(self.model.is_active == True)  # noqa: E712
        else:
            conditions.append(self.model.is_active == is_active)

        if category is not None:
            conditions.append(self.model.category == category)
        if resource is not None:
            conditions.append(self.model.resource == resource)
        if action is not None:
            conditions.append(self.model.action == action)

        # COUNT query
        count_stmt = select(func.count()).select_from(self.model).where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        # Data query
        col = getattr(self.model, order_by, self.model.created_at)
        order_col = col.desc() if order_direction.lower() == "desc" else col.asc()
        offset = (page - 1) * page_size

        data_stmt = (
            select(self.model)
            .where(and_(*conditions))
            .order_by(order_col)
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages

    # ------------------------------------------------------------------
    # Bulk create
    # ------------------------------------------------------------------

    async def bulk_create_permissions(
        self, permissions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Insert multiple permissions, skipping duplicates, and return created records."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        created = []
        for perm in permissions:
            stmt = (
                pg_insert(self.model)
                .values(**perm)
                .on_conflict_do_nothing(
                    index_elements=None,
                    constraint="uq_permissions_category_resource_action",
                )
                .returning(self.model)
            )
            result = await self.db.execute(stmt)
            row = result.scalars().first()
            if row is not None:
                created.append(row_to_dict(row))
        await self.db.flush()
        return created

    # ------------------------------------------------------------------
    # Distinct value helpers
    # ------------------------------------------------------------------

    async def get_categories(self) -> List[str]:
        """Return all distinct active permission categories."""
        stmt = (
            select(distinct(self.model.category))
            .where(self.model.is_active == True)  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return [row for (row,) in result.all() if row is not None]

    async def get_resources(self) -> List[str]:
        """Return all distinct active permission resources."""
        stmt = (
            select(distinct(self.model.resource))
            .where(self.model.is_active == True)  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return [row for (row,) in result.all() if row is not None]
