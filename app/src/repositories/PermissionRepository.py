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
            Permission.is_active.is_(True),
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
        page_size: int = 50,
        category: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        is_active: Optional[bool] = None,
        search_query: Optional[str] = None,
    ) -> Tuple[List[dict], int, int]:
        clauses = [Permission.is_active.is_(True) if is_active is None else Permission.is_active == is_active]

        if category is not None:
            clauses.append(Permission.category == category)
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

        count_stmt = select(func.count()).select_from(Permission).where(where_expr)
        total: int = (await self.db.execute(count_stmt)).scalar_one()
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Permission)
            .where(where_expr)
            .order_by(Permission.category.asc(), Permission.resource.asc(), Permission.action.asc())
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


    async def bulk_create_permissions(
        self,
        permissions: List[Dict[str, Any]],
    ) -> List[dict]:
        return await self.bulk_create(permissions)

    async def get_resources(self) -> List[str]:
        stmt = (
            select(distinct(Permission.resource))
            .where(Permission.is_active.is_(True))
            .where(Permission.resource.isnot(None))
            .order_by(Permission.resource)
        )
        result = await self.db.execute(stmt)
        return [row for (row,) in result.all()]

    async def get_actions(self) -> List[str]:
        stmt = (
            select(distinct(Permission.action))
            .where(Permission.is_active.is_(True))
            .where(Permission.action.isnot(None))
            .order_by(Permission.action)
        )
        result = await self.db.execute(stmt)
        return [row for (row,) in result.all()]
