"""
OrderTransactionService — business logic for order payment transactions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.models.OrderTransaction import OrderTransaction
from src.repositories.OrderRepository import OrderTransactionRepository


class OrderTransactionService:
    """Service for managing order payment transactions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OrderTransactionRepository(db)

    async def create_transaction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new order transaction record."""
        data.setdefault("payment_status", "unpaid")
        data.setdefault("currency", "INR")
        return await self.repo.create(data)

    async def get_transaction_by_order(
        self, order_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch the transaction record for a given order_id."""
        return await self.repo.get_by_order_id(order_id)

    async def get_by_id(self, transaction_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a transaction by its primary key."""
        return await self.repo.get_by_id(transaction_id)

    async def update_transaction(
        self, transaction_id: int, data: Dict[str, Any]
    ) -> bool:
        """Update payment fields on a transaction."""
        return await self.repo.update(transaction_id, data)

    async def get_paginated_transactions(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        payment_status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated transactions with optional filters."""
        conditions = [OrderTransaction.workspace_id == workspace_id]
        if persona_id is not None:
            conditions.append(OrderTransaction.persona_id == persona_id)
        if payment_status is not None:
            conditions.append(OrderTransaction.payment_status == payment_status)
        if start_date is not None:
            conditions.append(OrderTransaction.created_at >= start_date)
        if end_date is not None:
            conditions.append(OrderTransaction.created_at <= end_date)

        where_expr = and_(*conditions)
        count_stmt = (
            select(func.count()).select_from(OrderTransaction).where(where_expr)
        )
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
