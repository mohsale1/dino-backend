"""
OrderRepository — async SQLAlchemy 2.x repository for Order (line items) and OrderDetail.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, delete as sa_delete, func, select, update as sa_update
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

    async def get_by_order_id_for_persona(
        self,
        order_id: str,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return the order detail scoped to workspace and persona."""
        stmt = (
            select(OrderDetail)
            .where(
                OrderDetail.order_id == order_id,
                OrderDetail.workspace_id == workspace_id,
                OrderDetail.persona_id == persona_id,
                OrderDetail.is_active.is_(True),
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row else None

    async def update_status_for_persona(
        self,
        order_id: str,
        workspace_id: int,
        persona_id: int,
        new_status: str,
    ) -> bool:
        """Single-query UPDATE scoped to workspace and persona."""
        stmt = (
            sa_update(OrderDetail)
            .where(
                OrderDetail.order_id == order_id,
                OrderDetail.workspace_id == workspace_id,
                OrderDetail.persona_id == persona_id,
                OrderDetail.is_active.is_(True),
            )
            .values(status=new_status, updated_at=datetime.now(timezone.utc))
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def get_paginated_by_workspace(
        self,
        workspace_id: int,
        persona_id: int,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated order details for a workspace, always scoped to persona."""
        conditions = [
            OrderDetail.workspace_id == workspace_id,
            OrderDetail.persona_id == persona_id,
        ]
        if not include_deleted:
            conditions.append(OrderDetail.is_active.is_(True))
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

    # ------------------------------------------------------------------
    # PK overrides — Order uses `sino` as PK, not `id`.
    # BaseRepository.update/soft_delete/restore/delete all filter on
    # `self.model.id == entity_id` which silently matches zero rows here.
    # ------------------------------------------------------------------

    async def update(self, entity_id: Any, data: Dict[str, Any]) -> bool:
        """Update an Order row by sino (PK)."""
        if hasattr(self.model, "updated_at"):
            data = {**data, "updated_at": datetime.now(timezone.utc)}
        stmt = (
            sa_update(self.model)
            .where(self.model.sino == entity_id)
            .values(**data)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def soft_delete(self, entity_id: Any) -> bool:
        """Soft-delete an Order row by sino (PK)."""
        return await self.update(entity_id, {"is_active": False})

    async def restore(self, entity_id: Any) -> bool:
        """Restore a soft-deleted Order row by sino (PK)."""
        return await self.update(entity_id, {"is_active": True})

    async def delete(self, entity_id: Any) -> bool:
        """Hard-delete an Order row by sino (PK)."""
        stmt = (
            sa_delete(self.model)
            .where(self.model.sino == entity_id)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    # ------------------------------------------------------------------

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
        persona_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated transactions for a workspace, always scoped to persona."""
        where_expr = and_(
            OrderTransaction.workspace_id == workspace_id,
            OrderTransaction.persona_id == persona_id,
        )

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

    async def update_for_workspace(
        self,
        transaction_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Single-query UPDATE scoped to workspace and persona."""
        payload = {**data, "updated_at": datetime.now(timezone.utc)}
        stmt = (
            sa_update(OrderTransaction)
            .where(
                OrderTransaction.id == transaction_id,
                OrderTransaction.workspace_id == workspace_id,
                OrderTransaction.persona_id == persona_id,
            )
            .values(**payload)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0