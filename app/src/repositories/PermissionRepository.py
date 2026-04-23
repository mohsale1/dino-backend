from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Permission import Permission


class PermissionRepository(BaseRepository):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Permission, db)

    async def get_by_resource(self, resource: str) -> List[dict]:
        return await self.get_all(filters={"resource": resource})

    async def get_by_action(self, action: str) -> List[dict]:
        return await self.get_all(filters={"action": action})

    async def permission_exists(
        self,
        category: str,
        resource: str,
        action: str,
        exclude_id=None,
    ) -> bool:
        clauses = [
            Permission.category == category,
            Permission.resource == resource,
            Permission.action == action,
            Permission.is_active == True,
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
        if is_active is not None:
            clauses = [Permission.is_active == is_active]
        else:
            clauses = [Permission.is_active == True]

        if resource is not None:
            clauses.append(Permission.resource == resource)

        if action is not None:
            clauses.append(Permission.action == action)

        if search_query:
            q = search_query.strip()
            clauses.append(
                or_(
                    Permission.category.ilike(f"%{q}%"),
                    Permission.resource.ilike(f"%{q}%"),
                    Permission.action.ilike(f"%{q}%"),
                )
            )

        where_expr = and_(*clauses)

        count_stmt = (
            select(func.count())
            .select_from(Permission)
            .where(where_expr)
        )
        total_count: int = (await self.db.execute(count_stmt)).scalar_one()

        total_pages = max(1, (total_count + page_size - 1) // page_size)

        data_stmt = select(Permission).where(where_expr)

        order_expr = self._order_column(order_by, order_direction)
        if order_expr is not None:
            data_stmt = data_stmt.order_by(order_expr)

        data_stmt = data_stmt.limit(page_size).offset((page - 1) * page_size)
        result = await self.db.execute(data_stmt)
        items = [row_to_dict(row) for row in result.scalars().all()]

        return items, total_count, total_pages

    async def bulk_create_permissions(
        self,
        permissions: List[Dict[str, Any]],
    ) -> List[dict]:
        return await self.bulk_create(permissions)

    async def get_resources(self) -> List[str]:
        stmt = (
            select(distinct(Permission.resource))
            .where(Permission.is_active == True)
            .where(Permission.resource.isnot(None))
            .order_by(Permission.resource)
        )
        result = await self.db.execute(stmt)
        return [row for (row,) in result.all()]

    async def get_actions(self) -> List[str]:
        stmt = (
            select(distinct(Permission.action))
            .where(Permission.is_active == True)
            .where(Permission.action.isnot(None))
            .order_by(Permission.action)
        )
        result = await self.db.execute(stmt)
        return [row for (row,) in result.all()]
