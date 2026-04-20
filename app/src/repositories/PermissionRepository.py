"""
PermissionRepository — dino-application.

Handles CRUD and query operations for Permission records.
Permissions are global (not workspace-scoped).
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Permission import Permission


class PermissionRepository(BaseRepository):
    """Repository for global permission records."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Permission, db)

    # ------------------------------------------------------------------
    # Simple lookups (delegate to BaseRepository helpers)
    # ------------------------------------------------------------------

    async def get_by_name(self, name: str) -> Optional[dict]:
        """Return the permission with the given name, or None."""
        return await self.get_by_field("name", name)

    async def get_by_resource(self, resource: str) -> List[dict]:
        """Return all permissions for a resource."""
        return await self.get_all(filters={"resource": resource})

    async def get_by_action(self, action: str) -> List[dict]:
        """Return all permissions for an action."""
        return await self.get_all(filters={"action": action})

    # ------------------------------------------------------------------
    # Existence check
    # ------------------------------------------------------------------

    async def permission_exists(
        self,
        name: str,
        exclude_id=None,
    ) -> bool:
        """
        Return True when a non-deleted permission with *name* already exists.
        Pass *exclude_id* to skip the current record (update flow).
        """
        clauses = [
            Permission.name == name,
            Permission.is_active == True,  # noqa: E712
        ]

        if exclude_id is not None:
            clauses.append(Permission.id != exclude_id)

        stmt = (
            select(func.count())
            .select_from(Permission)
            .where(and_(*clauses))
        )
        count: int = (await self.db.execute(stmt)).scalar_one()
        return count > 0

    # ------------------------------------------------------------------
    # Paginated / filtered query
    # ------------------------------------------------------------------

    async def get_paginated_with_filters(
        self,
        page: int = 1,
        page_size: int = 10,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        is_active: Optional[bool] = None,
        search_query: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[dict], int, int]:
        """
        Paginated permission listing with optional filters and ILIKE search.

        Returns
        -------
        (items, total_count, total_pages)
        """
        # When is_active is explicitly passed use that value; otherwise default
        # to showing only active (non-deleted) records.
        if is_active is not None:
            clauses = [Permission.is_active == is_active]
        else:
            clauses = [Permission.is_active == True]  # noqa: E712

        if resource is not None:
            clauses.append(Permission.resource == resource)

        if action is not None:
            clauses.append(Permission.action == action)

        if search_query:
            q = search_query.strip()
            clauses.append(
                or_(
                    Permission.name.ilike(f"%{q}%"),
                    Permission.description.ilike(f"%{q}%"),
                    Permission.resource.ilike(f"%{q}%"),
                )
            )

        where_expr = and_(*clauses)

        # COUNT query
        count_stmt = (
            select(func.count())
            .select_from(Permission)
            .where(where_expr)
        )
        total_count: int = (await self.db.execute(count_stmt)).scalar_one()

        total_pages = max(1, (total_count + page_size - 1) // page_size)

        # DATA query
        data_stmt = select(Permission).where(where_expr)

        order_expr = self._order_column(order_by, order_direction)
        if order_expr is not None:
            data_stmt = data_stmt.order_by(order_expr)

        data_stmt = data_stmt.limit(page_size).offset((page - 1) * page_size)
        result = await self.db.execute(data_stmt)
        items = [row_to_dict(row) for row in result.scalars().all()]

        return items, total_count, total_pages

    # ------------------------------------------------------------------
    # Bulk create
    # ------------------------------------------------------------------

    async def bulk_create_permissions(
        self,
        permissions: List[Dict[str, Any]],
    ) -> List[dict]:
        """Insert multiple permissions in a single round-trip."""
        return await self.bulk_create(permissions)

    # ------------------------------------------------------------------
    # Distinct value helpers
    # ------------------------------------------------------------------

    async def get_resources(self) -> List[str]:
        """Return sorted distinct non-null resource values."""
        stmt = (
            select(distinct(Permission.resource))
            .where(Permission.is_active == True)  # noqa: E712
            .where(Permission.resource.isnot(None))
            .order_by(Permission.resource)
        )
        result = await self.db.execute(stmt)
        return [row for (row,) in result.all()]

    async def get_actions(self) -> List[str]:
        """Return sorted distinct non-null action values."""
        stmt = (
            select(distinct(Permission.action))
            .where(Permission.is_active == True)  # noqa: E712
            .where(Permission.action.isnot(None))
            .order_by(Permission.action)
        )
        result = await self.db.execute(stmt)
        return [row for (row,) in result.all()]
