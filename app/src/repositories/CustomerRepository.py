"""
CustomerRepository — async SQLAlchemy 2.x repository for the Customer model.
workspace_id and persona_id removed. mobile is globally unique.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Customer import Customer


class CustomerRepository(BaseRepository):
    """Repository for Customer entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Customer, db)

    async def get_by_mobile(self, mobile: str) -> Optional[Dict[str, Any]]:
        """Return the active customer with the given mobile number."""
        stmt = (
            select(Customer)
            .where(
                Customer.mobile == mobile,
                Customer.is_active.is_(True),
            )
            .limit(1)
        )
        row = (await self.db.execute(stmt)).scalars().first()
        return row_to_dict(row) if row else None

    async def get_paginated(
        self,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated active customers with optional name/mobile search."""
        conditions = [Customer.is_active.is_(True)]

        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    Customer.name.ilike(pattern),
                    Customer.mobile.ilike(pattern),
                )
            )

        where_expr = and_(*conditions)

        count_stmt = select(func.count()).select_from(Customer).where(where_expr)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Customer)
            .where(where_expr)
            .order_by(Customer.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages
