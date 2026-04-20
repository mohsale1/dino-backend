from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Order import Order
from src.repositories.CustomerRepository import CustomerRepository


class OrderRepository(BaseRepository):
    """Order repository — async SQLAlchemy 2.x."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Order, db)

    # ------------------------------------------------------------------
    # Simple lookups
    # ------------------------------------------------------------------

    async def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Return all active (non-deleted) orders for a workspace."""
        return await self.get_all(filters={"workspace_id": workspace_id})

    async def get_by_persona(self, persona_id: str) -> List[Dict[str, Any]]:
        """Return all active (non-deleted) orders for a persona."""
        return await self.get_all(filters={"persona_id": persona_id})

    async def get_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Return all active (non-deleted) orders with the given status."""
        return await self.get_all(filters={"status": status})

    async def get_by_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        """Return all active orders linked to a customer, newest first."""
        stmt = (
            select(Order)
            .where(
                Order.customer_id == customer_id,
                Order.is_active == True,  # noqa: E712
            )
            .order_by(Order.order_date.desc())
        )
        result = await self.db.execute(stmt)
        return [row_to_dict(row) for row in result.scalars().all()]

    # ------------------------------------------------------------------
    # Internal: shared query builder
    # ------------------------------------------------------------------

    def _build_order_clauses(
        self,
        scope_field: str,
        scope_value: str,
        filters: Optional[Dict[str, Any]],
        include_deleted: bool,
        start_date=None,
        end_date=None,
    ) -> list:
        """
        Build the full list of WHERE clauses for paginated order queries.

        Scope filter (workspace_id or persona_id) is always applied first,
        followed by the soft-delete guard (is_active == True), extra
        caller-supplied filters, and finally the date-range predicates
        against Order.order_date.
        """
        clauses = []

        # Scope
        scope_col = getattr(Order, scope_field)
        clauses.append(scope_col == scope_value)

        # Soft-delete guard — is_active == True means the record is live
        if not include_deleted:
            clauses.append(Order.is_active == True)  # noqa: E712

        # Extra equality filters (e.g. status, payment_status)
        if filters:
            for field, value in filters.items():
                col = getattr(Order, field, None)
                if col is not None:
                    clauses.append(col == value)

        # Date range — executed in SQL, not in memory
        if start_date is not None:
            clauses.append(Order.order_date >= start_date)
        if end_date is not None:
            clauses.append(Order.order_date <= end_date)

        return clauses

    async def _paginate_orders(
        self,
        clauses: list,
        page: int,
        page_size: int,
        order_by: str,
        order_direction: str,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Execute COUNT + SELECT queries and return (items, total, total_pages).
        """
        where_expr = and_(*clauses)

        # --- COUNT query ---
        count_stmt = (
            select(func.count())
            .select_from(Order)
            .where(where_expr)
        )
        total: int = (await self.db.execute(count_stmt)).scalar_one()
        total_pages = max(1, (total + page_size - 1) // page_size)

        # --- DATA query ---
        order_expr = self._order_column(order_by, order_direction)
        data_stmt = select(Order).where(where_expr)
        if order_expr is not None:
            data_stmt = data_stmt.order_by(order_expr)
        data_stmt = data_stmt.limit(page_size).offset((page - 1) * page_size)

        result = await self.db.execute(data_stmt)
        items = [row_to_dict(row) for row in result.scalars().all()]

        return items, total, total_pages

    # ------------------------------------------------------------------
    # Paginated queries
    # ------------------------------------------------------------------

    async def get_paginated_by_workspace(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
        include_deleted: bool = False,
        start_date=None,
        end_date=None,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Paginated orders scoped to a workspace with optional date range."""
        clauses = self._build_order_clauses(
            scope_field="workspace_id",
            scope_value=workspace_id,
            filters=filters,
            include_deleted=include_deleted,
            start_date=start_date,
            end_date=end_date,
        )
        return await self._paginate_orders(clauses, page, page_size, order_by, order_direction)

    async def get_paginated_by_persona(
        self,
        persona_id: str,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
        include_deleted: bool = False,
        start_date=None,
        end_date=None,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Paginated orders scoped to a persona with optional date range."""
        clauses = self._build_order_clauses(
            scope_field="persona_id",
            scope_value=persona_id,
            filters=filters,
            include_deleted=include_deleted,
            start_date=start_date,
            end_date=end_date,
        )
        return await self._paginate_orders(clauses, page, page_size, order_by, order_direction)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_orders_for_analytics(
        self,
        workspace_id: str,
        persona_id: Optional[str] = None,
        start_date=None,
        end_date=None,
    ) -> List[Dict[str, Any]]:
        """
        Return all matching orders (no pagination) for dashboard analytics.

        Filters applied in SQL:
          - workspace_id (required)
          - persona_id (optional)
          - order_date >= start_date (optional)
          - order_date <= end_date (optional)
          - is_active == True (always — excludes soft-deleted rows)
        """
        clauses: list = [
            Order.workspace_id == workspace_id,
            Order.is_active == True,  # noqa: E712
        ]

        if persona_id is not None:
            clauses.append(Order.persona_id == persona_id)

        if start_date is not None:
            clauses.append(Order.order_date >= start_date)
        if end_date is not None:
            clauses.append(Order.order_date <= end_date)

        stmt = (
            select(Order)
            .where(and_(*clauses))
            .order_by(Order.order_date.desc())
        )
        result = await self.db.execute(stmt)
        return [row_to_dict(row) for row in result.scalars().all()]
