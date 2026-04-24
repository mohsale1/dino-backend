"""
OrderRepository — async SQLAlchemy 2.x repository for Order (line items) and OrderDetail.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Order import Order
from src.models.OrderDetail import OrderDetail
from src.models.OrderTransaction import OrderTransaction


class OrderDetailRepository(BaseRepository):
    """Repository for OrderDetail (order headers)."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(OrderDetail, db)

    async def get_by_order_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Return the order detail with the given order_id."""
        stmt = (
            select(OrderDetail)
            .where(OrderDetail.order_id == order_id, OrderDetail.is_active.is_(True))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row else None

    async def get_paginated_by_workspace(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated order details for a workspace."""
        conditions = [OrderDetail.workspace_id == workspace_id]
        if not include_deleted:
            conditions.append(OrderDetail.is_active.is_(True))
        if persona_id is not None:
            conditions.append(OrderDetail.persona_id == persona_id)
        if status is not None:
            conditions.append(OrderDetail.status == status)

        where_expr = and_(*conditions)
        count_stmt = select(func.count()).select_from(OrderDetail).where(where_expr)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(OrderDetail)
            .where(where_expr)
            .order_by(OrderDetail.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages


class OrderRepository(BaseRepository):
    """Repository for Order line items (sino PK)."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Order, db)

    async def get_by_order_id(self, order_id: str) -> List[Dict[str, Any]]:
        """Return all line items for an order_id."""
        stmt = (
            select(Order)
            .where(Order.order_id == order_id, Order.is_active.is_(True))
            .order_by(Order.sino.asc())
        )
        result = await self.db.execute(stmt)
        return [row_to_dict(r) for r in result.scalars().all()]

    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active order line items for a workspace."""
        return await self.get_all(filters={"workspace_id": workspace_id})

    async def get_paginated_by_workspace(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated order line items for a workspace."""
        conditions = [Order.workspace_id == workspace_id, Order.is_active.is_(True)]
        if persona_id is not None:
            conditions.append(Order.persona_id == persona_id)

        where_expr = and_(*conditions)
        count_stmt = select(func.count()).select_from(Order).where(where_expr)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(Order)
            .where(where_expr)
            .order_by(Order.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages


class OrderTransactionRepository(BaseRepository):
    """Repository for OrderTransaction."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(OrderTransaction, db)

    async def get_by_order_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Return the transaction for an order_id."""
        stmt = (
            select(OrderTransaction)
            .where(OrderTransaction.order_id == order_id)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row else None

    async def get_paginated_by_workspace(
        self,
        workspace_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated transactions for a workspace."""
        conditions = [OrderTransaction.workspace_id == workspace_id]
        where_expr = and_(*conditions)

        count_stmt = select(func.count()).select_from(OrderTransaction).where(where_expr)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(OrderTransaction)
            .where(where_expr)
            .order_by(OrderTransaction.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages
