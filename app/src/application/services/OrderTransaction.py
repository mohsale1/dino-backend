"""
OrderTransactionService — business logic for order payment transactions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.core.Exceptions import BadRequestError
from src.models.OrderTransaction import OrderTransaction
from src.repositories.OrderRepository import OrderTransactionRepository

logger = logging.getLogger(__name__)


class OrderTransactionService:
    """Service for managing order payment transactions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OrderTransactionRepository(db)

    async def create_transaction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new payment transaction for an order.

        Raises
        ------
        BadRequestError
            If a transaction already exists for this order_id.
        """
        order_id = data.get("order_id")

        # Guard: one transaction per order
        existing = await self.repo.get_by_order_id(order_id)
        if existing:
            logger.warning(
                "transaction.create.duplicate order_id=%s workspace_id=%s",
                order_id, data.get("workspace_id"),
            )
            raise BadRequestError(
                f"A transaction already exists for order '{order_id}'. Use update instead."
            )

        data.setdefault("payment_status", "unpaid")
        data.setdefault("currency", "INR")

        transaction = await self.repo.create(data)
        logger.info(
            "transaction.created transaction_id=%s order_id=%s workspace_id=%s "
            "persona_id=%s payment_status=%s paid_amount=%s",
            transaction.get("id"), order_id, data.get("workspace_id"),
            data.get("persona_id"), transaction.get("payment_status"),
            transaction.get("paid_amount"),
        )
        return transaction

    async def get_transaction_by_order(
        self, order_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch the transaction record for a given order_id."""
        transaction = await self.repo.get_by_order_id(order_id)
        if transaction:
            logger.debug(
                "transaction.get.found order_id=%s transaction_id=%s status=%s",
                order_id, transaction.get("id"), transaction.get("payment_status"),
            )
        else:
            logger.debug("transaction.get.not_found order_id=%s", order_id)
        return transaction

    async def get_by_id(self, transaction_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a transaction by its primary key."""
        return await self.repo.get_by_id(transaction_id)

    async def update_transaction(
        self,
        transaction_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Single-query UPDATE of payment fields scoped to workspace and persona."""
        if not data:
            raise BadRequestError("No fields provided to update")

        updated = await self.repo.update_for_workspace(
            transaction_id, workspace_id, persona_id, data
        )
        if updated:
            logger.info(
                "transaction.updated transaction_id=%s workspace_id=%s "
                "persona_id=%s fields=%s",
                transaction_id, workspace_id, persona_id, list(data.keys()),
            )
        else:
            logger.warning(
                "transaction.update.not_found transaction_id=%s workspace_id=%s persona_id=%s",
                transaction_id, workspace_id, persona_id,
            )
        return updated

    async def get_paginated_transactions(
        self,
        workspace_id: int,
        persona_id: int,
        payment_status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated transactions scoped to workspace and persona."""
        conditions = [
            OrderTransaction.workspace_id == workspace_id,
            OrderTransaction.persona_id == persona_id,
        ]
        if payment_status is not None:
            conditions.append(OrderTransaction.payment_status == payment_status)
        if start_date is not None:
            conditions.append(OrderTransaction.created_at >= start_date)
        if end_date is not None:
            conditions.append(OrderTransaction.created_at <= end_date)

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

        result = []
        for idx, row in enumerate(rows, start=offset + 1):
            d = row_to_dict(row)
            d["index"] = idx
            result.append(d)

        logger.debug(
            "transaction.list workspace_id=%s persona_id=%s payment_status=%s "
            "total=%s returned=%s page=%s",
            workspace_id, persona_id, payment_status, total, len(result), page,
        )
        return result, total, total_pages
