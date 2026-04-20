"""
PermissionRepository — async SQLAlchemy 2.x repository for the Permission model.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import distinct, func, or_, select
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

    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Return the first active permission with the given name."""
        stmt = (
            select(self.model)
            .where(self.model.name == name)
            .where(self.model.is_active == True)  # noqa: E712
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row is not None else None

    async def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Return all active permissions in the given category."""
        return await self.get_all(filters={"category": category})

    async def get_by_resource(self, resource: str) -> List[Dict[str, Any]]:
        """Return all active permissions targeting the given resource."""
        return await self.get_all(filters={"resource": resource})

    async def get_by_action(self, action: str) -> List[Dict[str, Any]]:
        """Return all active permissions with the given action."""
        return await self.get_all(filters={"action": action})

    async def get_system_permissions(self) -> List[Dict[str, Any]]:
        """Return all active built-in (is_system=True) permissions."""
        return await self.get_all(filters={"is_system": True})

    # ------------------------------------------------------------------
    # Existence check
    # ------------------------------------------------------------------

    async def permission_exists(
        self, name: str, exclude_id: Optional[str] = None
    ) -> bool:
        """
        Return True if an active permission with the given name exists.
        Optionally exclude a specific record (useful for update validation).
        """
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.name == name)
            .where(self.model.is_active == True)  # noqa: E712
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
        page_size: int = 10,
        category: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        is_active: Optional[bool] = None,
        search_query: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Return (items, total_count) with optional filtering and pagination.

        When is_active is None (default), only active records are returned.
        When is_active is explicitly provided, that value is used as the filter.

        search_query performs a case-insensitive ILIKE match against
        name, description, and resource columns.
        """
        base_conditions = []

        # Default guard: show only active records unless caller explicitly filters
        if is_active is None:
            base_conditions.append(self.model.is_active == True)  # noqa: E712
        else:
            base_conditions.append(self.model.is_active == is_active)

        if category is not None:
            base_conditions.append(self.model.category == category)
        if resource is not None:
            base_conditions.append(self.model.resource == resource)
        if action is not None:
            base_conditions.append(self.model.action == action)
        if search_query:
            pattern = f"%{search_query}%"
            base_conditions.append(
                or_(
                    self.model.name.ilike(pattern),
                    self.model.description.ilike(pattern),
                    self.model.resource.ilike(pattern),
                )
            )

        # COUNT query
        count_stmt = (
            select(func.count())
            .select_from(self.model)
            .where(*base_conditions)
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one() or 0

        # Data query
        col = getattr(self.model, order_by, self.model.created_at)
        order_col = col.desc() if order_direction.lower() == "desc" else col.asc()
        offset = (page - 1) * page_size

        data_stmt = (
            select(self.model)
            .where(*base_conditions)
            .order_by(order_col)
            .limit(page_size)
            .offset(offset)
        )
        data_result = await self.db.execute(data_stmt)
        rows = data_result.scalars().all()

        return [row_to_dict(r) for r in rows], total

    # ------------------------------------------------------------------
    # Bulk create
    # ------------------------------------------------------------------

    async def bulk_create_permissions(
        self, permissions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Insert multiple permissions and return the created records."""
        return await self.bulk_create(permissions)

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

    async def get_actions(self) -> List[str]:
        """Return all distinct active permission actions."""
        stmt = (
            select(distinct(self.model.action))
            .where(self.model.is_active == True)  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return [row for (row,) in result.all() if row is not None]
