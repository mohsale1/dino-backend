"""
ApplicationDashboardService — aggregated metrics for the application dashboard.
All multi-query methods use asyncio.gather for parallel execution.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, case, cast, extract, func, select, Date
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.Category import Category
from src.models.Customer import Customer
from src.models.Item import Item
from src.models.Order import Order
from src.models.OrderDetail import OrderDetail
from src.models.OrderTransaction import OrderTransaction
from src.models.Table import Table


class ApplicationDashboardService:
    """Service for dashboard analytics and reporting."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _order_conditions(
        self, workspace_id: int, persona_id: Optional[int] = None
    ) -> list:
        """Base WHERE conditions for order_details queries."""
        conditions = [
            OrderDetail.workspace_id == workspace_id,
            OrderDetail.is_active.is_(True),
        ]
        if persona_id is not None:
            conditions.append(OrderDetail.persona_id == persona_id)
        return conditions

    def _order_line_conditions(
        self, workspace_id: int, persona_id: Optional[int] = None
    ) -> list:
        """Base WHERE conditions for orders (line items) queries."""
        conditions = [
            Order.workspace_id == workspace_id,
            Order.is_active.is_(True),
        ]
        if persona_id is not None:
            conditions.append(Order.persona_id == persona_id)
        return conditions

    def _transaction_conditions(
        self, workspace_id: int, persona_id: Optional[int] = None
    ) -> list:
        """Base WHERE conditions for order_transactions queries."""
        conditions = [OrderTransaction.workspace_id == workspace_id]
        if persona_id is not None:
            conditions.append(OrderTransaction.persona_id == persona_id)
        return conditions

    # ------------------------------------------------------------------
    # Stats — all sub-queries parallelised
    # ------------------------------------------------------------------

    async def get_dashboard_stats(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return key dashboard metrics. All 7 queries run in parallel."""
        now = datetime.now(timezone.utc)
        today = now.date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        base = self._order_conditions(workspace_id, persona_id)

        async def _count_revenue(extra: list) -> Dict[str, Any]:
            stmt = select(
                func.count(OrderDetail.id).label("orders"),
                func.coalesce(func.sum(OrderDetail.total_amount), 0).label("revenue"),
            ).where(and_(*base, *extra))
            row = (await self.db.execute(stmt)).one()
            return {"orders": row.orders, "revenue": float(row.revenue)}

        async def _pending_orders() -> int:
            stmt = select(func.count(OrderDetail.id)).where(
                and_(*base, OrderDetail.status == "pending")
            )
            return (await self.db.execute(stmt)).scalar_one() or 0

        async def _table_stats() -> Dict[str, int]:
            conds = [Table.is_active.is_(True)]
            if persona_id is not None:
                conds.append(Table.persona_id == persona_id)
            stmt = select(
                func.count(Table.id).label("total"),
                func.count(case((Table.status == "occupied", 1))).label("occupied"),
                func.count(case((Table.status == "available", 1))).label("available"),
            ).where(and_(*conds))
            row = (await self.db.execute(stmt)).one()
            return {
                "active_tables": row.total,
                "occupied_tables": row.occupied,
                "available_tables": row.available,
            }

        async def _total_customers() -> int:
            stmt = select(func.count(Customer.id)).where(Customer.is_active.is_(True))
            return (await self.db.execute(stmt)).scalar_one() or 0

        async def _total_items() -> int:
            conds = [Item.is_active.is_(True)]
            if persona_id is not None:
                conds.append(Item.persona_id == persona_id)
            stmt = select(func.count(Item.id)).where(and_(*conds))
            return (await self.db.execute(stmt)).scalar_one() or 0

        (
            today_data,
            week_data,
            month_data,
            pending,
            table_data,
            total_customers,
            total_items,
        ) = await asyncio.gather(
            _count_revenue([cast(OrderDetail.created_at, Date) == today]),
            _count_revenue([cast(OrderDetail.created_at, Date) >= week_start]),
            _count_revenue([cast(OrderDetail.created_at, Date) >= month_start]),
            _pending_orders(),
            _table_stats(),
            _total_customers(),
            _total_items(),
        )

        return {
            "today": today_data,
            "this_week": week_data,
            "this_month": month_data,
            "pending_orders": pending,
            "total_customers": total_customers,
            "total_items": total_items,
            **table_data,
        }

    # ------------------------------------------------------------------
    # Revenue trend
    # ------------------------------------------------------------------

    async def get_revenue_trend(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Return revenue + order count per day for the last N days."""
        since = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
        base = self._order_conditions(workspace_id, persona_id)

        stmt = (
            select(
                cast(OrderDetail.created_at, Date).label("day"),
                func.count(OrderDetail.id).label("orders"),
                func.coalesce(func.sum(OrderDetail.total_amount), 0).label("revenue"),
            )
            .where(and_(*base, cast(OrderDetail.created_at, Date) >= since))
            .group_by(cast(OrderDetail.created_at, Date))
            .order_by(cast(OrderDetail.created_at, Date).asc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {"day": str(r.day), "orders": r.orders, "revenue": float(r.revenue)}
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Orders by status
    # ------------------------------------------------------------------

    async def get_orders_by_status(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> Dict[str, int]:
        """Return order counts grouped by status — single query."""
        base = self._order_conditions(workspace_id, persona_id)
        stmt = select(
            func.count(case((OrderDetail.status == "pending", 1))).label("pending"),
            func.count(case((OrderDetail.status == "confirmed", 1))).label("confirmed"),
            func.count(case((OrderDetail.status == "preparing", 1))).label("preparing"),
            func.count(case((OrderDetail.status == "ready", 1))).label("ready"),
            func.count(case((OrderDetail.status == "served", 1))).label("served"),
            func.count(case((OrderDetail.status == "completed", 1))).label("completed"),
            func.count(case((OrderDetail.status == "cancelled", 1))).label("cancelled"),
        ).where(and_(*base))
        row = (await self.db.execute(stmt)).one()
        return {
            "pending": row.pending,
            "confirmed": row.confirmed,
            "preparing": row.preparing,
            "ready": row.ready,
            "served": row.served,
            "completed": row.completed,
            "cancelled": row.cancelled,
        }

    # ------------------------------------------------------------------
    # Orders by type
    # ------------------------------------------------------------------

    async def get_orders_by_type(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> Dict[str, int]:
        """Return order counts grouped by order_type — single query."""
        base = self._order_conditions(workspace_id, persona_id)
        stmt = select(
            func.count(case((OrderDetail.order_type == "dine_in", 1))).label("dine_in"),
            func.count(case((OrderDetail.order_type == "takeaway", 1))).label("takeaway"),
            func.count(case((OrderDetail.order_type == "delivery", 1))).label("delivery"),
        ).where(and_(*base))
        row = (await self.db.execute(stmt)).one()
        return {
            "dine_in": row.dine_in,
            "takeaway": row.takeaway,
            "delivery": row.delivery,
        }

    # ------------------------------------------------------------------
    # Top items
    # ------------------------------------------------------------------

    async def get_top_items(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return most ordered items by total quantity sold."""
        base = self._order_line_conditions(workspace_id, persona_id)
        stmt = (
            select(
                Order.item_id,
                Order.item_name,
                func.sum(Order.quantity).label("total_quantity"),
                func.coalesce(func.sum(Order.line_total), 0).label("total_revenue"),
                func.count(Order.sino).label("order_count"),
            )
            .where(and_(*base))
            .group_by(Order.item_id, Order.item_name)
            .order_by(func.sum(Order.quantity).desc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "item_id": r.item_id,
                "item_name": r.item_name,
                "total_quantity": r.total_quantity,
                "total_revenue": float(r.total_revenue),
                "order_count": r.order_count,
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Payment summary — parallelised
    # ------------------------------------------------------------------

    async def get_payment_summary(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return payment breakdown by status and method — 2 queries in parallel."""
        base = self._transaction_conditions(workspace_id, persona_id)
        where_expr = and_(*base)

        async def _by_status():
            stmt = (
                select(
                    OrderTransaction.payment_status,
                    func.count(OrderTransaction.id).label("count"),
                    func.coalesce(func.sum(OrderTransaction.paid_amount), 0).label("total"),
                )
                .where(where_expr)
                .group_by(OrderTransaction.payment_status)
            )
            return (await self.db.execute(stmt)).all()

        async def _by_method():
            stmt = (
                select(
                    OrderTransaction.payment_method,
                    func.count(OrderTransaction.id).label("count"),
                    func.coalesce(func.sum(OrderTransaction.paid_amount), 0).label("total"),
                )
                .where(where_expr)
                .group_by(OrderTransaction.payment_method)
            )
            return (await self.db.execute(stmt)).all()

        status_rows, method_rows = await asyncio.gather(_by_status(), _by_method())

        return {
            "by_status": [
                {"payment_status": r.payment_status, "count": r.count, "total": float(r.total)}
                for r in status_rows
            ],
            "by_method": [
                {"payment_method": r.payment_method, "count": r.count, "total": float(r.total)}
                for r in method_rows
            ],
        }

    # ------------------------------------------------------------------
    # Hourly orders — today
    # ------------------------------------------------------------------

    async def get_hourly_orders(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return order counts + revenue grouped by hour of day for today."""
        today = datetime.now(timezone.utc).date()
        base = self._order_conditions(workspace_id, persona_id)

        stmt = (
            select(
                extract("hour", OrderDetail.created_at).label("hour"),
                func.count(OrderDetail.id).label("orders"),
                func.coalesce(func.sum(OrderDetail.total_amount), 0).label("revenue"),
            )
            .where(and_(*base, cast(OrderDetail.created_at, Date) == today))
            .group_by(extract("hour", OrderDetail.created_at))
            .order_by(extract("hour", OrderDetail.created_at).asc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {"hour": int(r.hour), "orders": r.orders, "revenue": float(r.revenue)}
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Category revenue — NEW
    # ------------------------------------------------------------------

    async def get_category_revenue(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Return revenue + order count per category for the last N days.
        Joins order line items → items → categories.
        Useful for pie/bar charts showing which categories drive revenue.
        """
        since = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
        base = self._order_line_conditions(workspace_id, persona_id)

        stmt = (
            select(
                Category.id.label("category_id"),
                Category.name.label("category_name"),
                func.coalesce(func.sum(Order.line_total), 0).label("revenue"),
                func.sum(Order.quantity).label("total_quantity"),
                func.count(Order.sino).label("order_count"),
            )
            .join(Item, Item.id == Order.item_id)
            .join(Category, Category.id == Item.category_id)
            .where(
                and_(
                    *base,
                    cast(Order.created_at, Date) >= since,
                    Category.is_active.is_(True),
                )
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Order.line_total).desc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "category_id": r.category_id,
                "category_name": r.category_name,
                "revenue": float(r.revenue),
                "total_quantity": r.total_quantity,
                "order_count": r.order_count,
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Table utilisation — NEW
    # ------------------------------------------------------------------

    async def get_table_utilisation(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Return order count + revenue per table for the last N days.
        Useful for heatmap/bar showing busiest tables.
        """
        since = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
        base = self._order_conditions(workspace_id, persona_id)

        stmt = (
            select(
                OrderDetail.table_id,
                Table.table_number,
                func.count(OrderDetail.id).label("order_count"),
                func.coalesce(func.sum(OrderDetail.total_amount), 0).label("revenue"),
            )
            .join(Table, Table.id == OrderDetail.table_id)
            .where(
                and_(
                    *base,
                    OrderDetail.table_id.isnot(None),
                    cast(OrderDetail.created_at, Date) >= since,
                    Table.is_active.is_(True),
                )
            )
            .group_by(OrderDetail.table_id, Table.table_number)
            .order_by(func.count(OrderDetail.id).desc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "table_id": r.table_id,
                "table_number": r.table_number,
                "order_count": r.order_count,
                "revenue": float(r.revenue),
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Recent orders — NEW
    # ------------------------------------------------------------------

    async def get_recent_orders(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Return the most recent N orders with key fields.
        Useful for a live feed / activity widget on the dashboard.
        """
        base = self._order_conditions(workspace_id, persona_id)
        stmt = (
            select(
                OrderDetail.id,
                OrderDetail.order_id,
                OrderDetail.customer_name,
                OrderDetail.status,
                OrderDetail.order_type,
                OrderDetail.total_amount,
                OrderDetail.table_id,
                OrderDetail.created_at,
            )
            .where(and_(*base))
            .order_by(OrderDetail.created_at.desc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "id": r.id,
                "order_id": r.order_id,
                "customer_name": r.customer_name,
                "status": r.status,
                "order_type": r.order_type,
                "total_amount": float(r.total_amount),
                "table_id": r.table_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Customer stats — NEW
    # ------------------------------------------------------------------

    async def get_customer_stats(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Return new vs returning customer counts and top customers by spend.
        New = first order within the last N days.
        Returning = ordered before AND within the last N days.
        """
        since = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
        base = self._order_conditions(workspace_id, persona_id)

        async def _new_vs_returning():
            # Subquery: first order date per customer
            first_order = (
                select(
                    OrderDetail.customer_id,
                    func.min(cast(OrderDetail.created_at, Date)).label("first_date"),
                )
                .where(and_(*base, OrderDetail.customer_id.isnot(None)))
                .group_by(OrderDetail.customer_id)
                .subquery()
            )
            stmt = select(
                func.count(case((first_order.c.first_date >= since, 1))).label("new_customers"),
                func.count(case((first_order.c.first_date < since, 1))).label("returning_customers"),
            ).select_from(first_order)
            row = (await self.db.execute(stmt)).one()
            return {"new_customers": row.new_customers, "returning_customers": row.returning_customers}

        async def _top_customers():
            stmt = (
                select(
                    OrderDetail.customer_id,
                    OrderDetail.customer_name,
                    func.count(OrderDetail.id).label("order_count"),
                    func.coalesce(func.sum(OrderDetail.total_amount), 0).label("total_spend"),
                )
                .where(
                    and_(
                        *base,
                        OrderDetail.customer_id.isnot(None),
                        cast(OrderDetail.created_at, Date) >= since,
                    )
                )
                .group_by(OrderDetail.customer_id, OrderDetail.customer_name)
                .order_by(func.sum(OrderDetail.total_amount).desc())
                .limit(10)
            )
            rows = (await self.db.execute(stmt)).all()
            return [
                {
                    "customer_id": r.customer_id,
                    "customer_name": r.customer_name,
                    "order_count": r.order_count,
                    "total_spend": float(r.total_spend),
                }
                for r in rows
            ]

        counts, top = await asyncio.gather(_new_vs_returning(), _top_customers())
        return {**counts, "top_customers": top}

    # ------------------------------------------------------------------
    # Full dashboard — all in parallel
    # ------------------------------------------------------------------

    async def get_full_dashboard(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Aggregate all dashboard data in one call — fully parallelised."""
        (
            stats,
            orders_by_status,
            orders_by_type,
            top_items,
            payment_summary,
            hourly_orders,
            revenue_trend,
            category_revenue,
            table_utilisation,
            recent_orders,
            customer_stats,
        ) = await asyncio.gather(
            self.get_dashboard_stats(workspace_id, persona_id),
            self.get_orders_by_status(workspace_id, persona_id),
            self.get_orders_by_type(workspace_id, persona_id),
            self.get_top_items(workspace_id, persona_id),
            self.get_payment_summary(workspace_id, persona_id),
            self.get_hourly_orders(workspace_id, persona_id),
            self.get_revenue_trend(workspace_id, persona_id, days=30),
            self.get_category_revenue(workspace_id, persona_id, days=30),
            self.get_table_utilisation(workspace_id, persona_id, days=7),
            self.get_recent_orders(workspace_id, persona_id, limit=20),
            self.get_customer_stats(workspace_id, persona_id, days=30),
        )
        return {
            "stats": stats,
            "orders_by_status": orders_by_status,
            "orders_by_type": orders_by_type,
            "top_items": top_items,
            "payment_summary": payment_summary,
            "hourly_orders": hourly_orders,
            "revenue_trend": revenue_trend,
            "category_revenue": category_revenue,
            "table_utilisation": table_utilisation,
            "recent_orders": recent_orders,
            "customer_stats": customer_stats,
        }
