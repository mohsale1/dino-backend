"""
ApplicationDashboardService — aggregated metrics for the application dashboard.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

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

    def _order_base(
        self, workspace_id: int, persona_id: Optional[int]
    ) -> list:
        conditions = [
            OrderDetail.workspace_id == workspace_id,
            OrderDetail.is_active == True,  # noqa: E712
        ]
        if persona_id is not None:
            conditions.append(OrderDetail.persona_id == persona_id)
        return conditions

    # ------------------------------------------------------------------
    # Dashboard stats
    # ------------------------------------------------------------------

    async def get_dashboard_stats(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return key dashboard metrics."""
        now = datetime.now(timezone.utc)
        today = now.date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        base = self._order_base(workspace_id, persona_id)

        async def _count_revenue(extra_conditions: list) -> Dict[str, Any]:
            conds = base + extra_conditions
            stmt = select(
                func.count(OrderDetail.id).label("orders"),
                func.coalesce(func.sum(OrderDetail.total_amount), 0).label("revenue"),
            ).where(and_(*conds))
            row = (await self.db.execute(stmt)).one()
            return {"orders": row.orders, "revenue": float(row.revenue)}

        today_data = await _count_revenue([func.date(OrderDetail.created_at) == today])
        week_data = await _count_revenue([func.date(OrderDetail.created_at) >= week_start])
        month_data = await _count_revenue([func.date(OrderDetail.created_at) >= month_start])

        # Pending orders
        pending_stmt = select(func.count(OrderDetail.id)).where(
            and_(*base, OrderDetail.status == "pending")
        )
        pending_orders = (await self.db.execute(pending_stmt)).scalar_one() or 0

        # Tables
        table_conditions = [Table.workspace_id == workspace_id, Table.is_active == True]  # noqa: E712
        active_tables_stmt = select(func.count(Table.id)).where(and_(*table_conditions))
        active_tables = (await self.db.execute(active_tables_stmt)).scalar_one() or 0

        occupied_stmt = select(func.count(Table.id)).where(
            and_(*table_conditions, Table.status == "occupied")
        )
        occupied_tables = (await self.db.execute(occupied_stmt)).scalar_one() or 0

        # Customers
        customer_conditions = [
            Customer.workspace_id == workspace_id,
            Customer.is_active == True,  # noqa: E712
        ]
        customers_stmt = select(func.count(Customer.id)).where(and_(*customer_conditions))
        total_customers = (await self.db.execute(customers_stmt)).scalar_one() or 0

        # Items
        item_conditions = [
            Item.workspace_id == workspace_id,
            Item.is_active == True,  # noqa: E712
        ]
        items_stmt = select(func.count(Item.id)).where(and_(*item_conditions))
        total_items = (await self.db.execute(items_stmt)).scalar_one() or 0

        return {
            "today": today_data,
            "this_week": week_data,
            "this_month": month_data,
            "active_tables": active_tables,
            "occupied_tables": occupied_tables,
            "total_customers": total_customers,
            "total_items": total_items,
            "pending_orders": pending_orders,
        }

    async def get_revenue_trend(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Return revenue per day for the last N days."""
        since = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
        base = self._order_base(workspace_id, persona_id)
        base.append(func.date(OrderDetail.created_at) >= since)

        stmt = (
            select(
                func.date(OrderDetail.created_at).label("day"),
                func.count(OrderDetail.id).label("orders"),
                func.coalesce(func.sum(OrderDetail.total_amount), 0).label("revenue"),
            )
            .where(and_(*base))
            .group_by(func.date(OrderDetail.created_at))
            .order_by(func.date(OrderDetail.created_at).asc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "day": str(r.day),
                "orders": r.orders,
                "revenue": float(r.revenue),
            }
            for r in rows
        ]

    async def get_orders_by_status(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> Dict[str, int]:
        """Return order counts grouped by status."""
        base = self._order_base(workspace_id, persona_id)
        stmt = select(
            func.count(case((OrderDetail.status == "pending", 1))).label("pending"),
            func.count(case((OrderDetail.status == "confirmed", 1))).label("confirmed"),
            func.count(case((OrderDetail.status == "preparing", 1))).label("preparing"),
            func.count(case((OrderDetail.status == "ready", 1))).label("ready"),
            func.count(case((OrderDetail.status == "served", 1))).label("served"),
            func.count(case((OrderDetail.status == "cancelled", 1))).label("cancelled"),
        ).where(and_(*base))
        row = (await self.db.execute(stmt)).one()
        return {
            "pending": row.pending,
            "confirmed": row.confirmed,
            "preparing": row.preparing,
            "ready": row.ready,
            "served": row.served,
            "cancelled": row.cancelled,
        }

    async def get_orders_by_type(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> Dict[str, int]:
        """Return order counts grouped by order_type."""
        base = self._order_base(workspace_id, persona_id)
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

    async def get_top_items(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return most ordered items by total quantity sold."""
        conditions = [
            Order.workspace_id == workspace_id,
            Order.is_active == True,  # noqa: E712
        ]
        if persona_id is not None:
            conditions.append(Order.persona_id == persona_id)

        stmt = (
            select(
                Order.item_id,
                Order.item_name,
                func.sum(Order.quantity).label("total_quantity"),
                func.sum(Order.line_total).label("total_revenue"),
                func.count(Order.sino).label("order_count"),
            )
            .where(and_(*conditions))
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

    async def get_payment_summary(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return payment breakdown by status and method from order_transactions."""
        conditions = [OrderTransaction.workspace_id == workspace_id]
        if persona_id is not None:
            conditions.append(OrderTransaction.persona_id == persona_id)

        where_expr = and_(*conditions)

        # By status
        status_stmt = select(
            OrderTransaction.payment_status,
            func.count(OrderTransaction.id).label("count"),
            func.coalesce(func.sum(OrderTransaction.paid_amount), 0).label("total"),
        ).where(where_expr).group_by(OrderTransaction.payment_status)
        status_rows = (await self.db.execute(status_stmt)).all()

        # By method
        method_stmt = select(
            OrderTransaction.payment_method,
            func.count(OrderTransaction.id).label("count"),
            func.coalesce(func.sum(OrderTransaction.paid_amount), 0).label("total"),
        ).where(where_expr).group_by(OrderTransaction.payment_method)
        method_rows = (await self.db.execute(method_stmt)).all()

        return {
            "by_status": [
                {
                    "payment_status": r.payment_status,
                    "count": r.count,
                    "total": float(r.total),
                }
                for r in status_rows
            ],
            "by_method": [
                {
                    "payment_method": r.payment_method,
                    "count": r.count,
                    "total": float(r.total),
                }
                for r in method_rows
            ],
        }

    async def get_hourly_orders(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return order counts grouped by hour of day for today."""
        today = datetime.now(timezone.utc).date()
        base = self._order_base(workspace_id, persona_id)
        base.append(func.date(OrderDetail.created_at) == today)

        stmt = (
            select(
                extract("hour", OrderDetail.created_at).label("hour"),
                func.count(OrderDetail.id).label("orders"),
                func.coalesce(func.sum(OrderDetail.total_amount), 0).label("revenue"),
            )
            .where(and_(*base))
            .group_by(extract("hour", OrderDetail.created_at))
            .order_by(extract("hour", OrderDetail.created_at).asc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "hour": int(r.hour),
                "orders": r.orders,
                "revenue": float(r.revenue),
            }
            for r in rows
        ]

    async def get_full_dashboard(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Aggregate all dashboard data in one call."""
        stats = await self.get_dashboard_stats(workspace_id, persona_id)
        orders_by_status = await self.get_orders_by_status(workspace_id, persona_id)
        orders_by_type = await self.get_orders_by_type(workspace_id, persona_id)
        top_items = await self.get_top_items(workspace_id, persona_id)
        payment_summary = await self.get_payment_summary(workspace_id, persona_id)
        hourly_orders = await self.get_hourly_orders(workspace_id, persona_id)
        revenue_trend = await self.get_revenue_trend(workspace_id, persona_id, days=30)

        return {
            "stats": stats,
            "orders_by_status": orders_by_status,
            "orders_by_type": orders_by_type,
            "top_items": top_items,
            "payment_summary": payment_summary,
            "hourly_orders": hourly_orders,
            "revenue_trend": revenue_trend,
        }
