import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.models.Item import Item
from src.repositories.OrderRepository import OrderRepository
from src.repositories.PersonaRepository import PersonaRepository


class OrderService(BaseService):
    """Order service"""

    def __init__(self, db: AsyncSession):
        super().__init__(OrderRepository(db))
        self.repo = self.repository
        self._db = db
        self._persona_repo = PersonaRepository(db)

    def generate_order_number(self, workspace_id: Any) -> str:
        """
        Generate a collision-resistant order number.

        Format: ORD-{workspace_id}-{timestamp}-{token}

        The token is 8 random bytes rendered as 16 hex characters, giving
        2^64 possible values per timestamp bucket — collisions are
        astronomically unlikely even under high concurrency.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        token = secrets.token_hex(8)
        return f"ORD-{workspace_id}-{timestamp}-{token}"

    async def _fetch_item_prices(self, item_ids: List[Any]) -> Dict[Any, float]:
        """
        Fetch authoritative prices for the given item IDs from the database.

        Returns a mapping of {item_id: price}.  Items not found in the DB are
        omitted; the caller is responsible for detecting missing IDs.
        """
        if not item_ids:
            return {}

        stmt = select(Item.id, Item.price).where(Item.id.in_(item_ids))
        result = await self._db.execute(stmt)
        return {row.id: float(row.price) for row in result.all()}

    async def create_order(self, data: Dict[str, Any]) -> str:
        """
        Create a new order and return the new order ID.

        Price integrity
        ---------------
        Client-supplied prices are NEVER trusted.  The service fetches the
        authoritative unit price for every line item from the database and
        recalculates the subtotal server-side.  The `items` list in *data*
        must contain `item_id` and `quantity`; any client-provided price
        fields are ignored.

        Raises ValueError when an item_id is not found in the database.
        """
        # Resolve workspace_id from persona when not already supplied.
        persona_id = data.get("persona_id")
        if persona_id and "workspace_id" not in data:
            persona = await self._persona_repo.get_by_id(persona_id)
            if persona:
                data["workspace_id"] = persona.get("workspace_id")

        workspace_id = data.get("workspace_id")
        data["order_number"] = self.generate_order_number(workspace_id)

        # Recalculate total_amount server-side from DB prices.
        items: List[Dict[str, Any]] = data.get("items", [])
        if items:
            item_ids = [item["item_id"] for item in items]
            price_map = await self._fetch_item_prices(item_ids)

            missing = [iid for iid in item_ids if iid not in price_map]
            if missing:
                raise ValueError(
                    f"The following item IDs were not found: {missing}"
                )

            total_amount = sum(
                price_map[item["item_id"]] * int(item["quantity"])
                for item in items
            )
            data["total_amount"] = round(total_amount, 2)
        else:
            data["total_amount"] = 0.0

        if "status" not in data:
            data["status"] = "pending"

        if "payment_status" not in data:
            data["payment_status"] = "unpaid"

        data["order_date"] = datetime.now(timezone.utc)

        created = await self.create(data)
        return created["id"]

    async def update_order_status(self, order_id: str, status: str) -> bool:
        """Update order status"""
        return await self.update(order_id, {"status": status})

    async def update_payment_status(self, order_id: str, payment_status: str) -> bool:
        """Update payment status"""
        return await self.update(order_id, {"payment_status": payment_status})

    async def get_statistics(
        self,
        workspace_id: str,
        persona_id: Optional[str] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Return aggregated order statistics for the given scope and date range."""

        def _parse_dt(value: Any) -> Optional[datetime]:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            try:
                dt = datetime.fromisoformat(str(value))
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                return None

        start_dt = _parse_dt(start_date)
        end_dt = _parse_dt(end_date)

        orders = await self.repo.get_orders_for_analytics(
            workspace_id, persona_id, start_dt, end_dt
        )

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        total_orders = len(orders)
        total_revenue = 0.0
        non_cancelled_count = 0
        orders_by_status: Dict[str, int] = {}
        today_orders = 0
        today_revenue = 0.0

        for order in orders:
            order_status = order.get("status", "unknown")
            orders_by_status[order_status] = orders_by_status.get(order_status, 0) + 1

            # Resolve the order timestamp.
            created = order.get("order_date") or order.get("created_at")
            if created is not None:
                if isinstance(created, str):
                    try:
                        created = datetime.fromisoformat(created)
                    except ValueError:
                        created = None
                if isinstance(created, datetime) and created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)

            if order_status != "cancelled":
                amount = float(order.get("total_amount") or 0)
                total_revenue += amount
                non_cancelled_count += 1

                if isinstance(created, datetime) and today_start <= created <= today_end:
                    today_orders += 1
                    today_revenue += amount
            else:
                # Cancelled orders still count toward today's order tally for
                # status-breakdown purposes, but not toward revenue.
                if isinstance(created, datetime) and today_start <= created <= today_end:
                    today_orders += 1

        # Use non-cancelled order count as denominator so that a workspace
        # with only cancelled orders does not produce a misleading average.
        avg_order_value = (
            total_revenue / non_cancelled_count if non_cancelled_count > 0 else 0.0
        )

        return {
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "orders_by_status": orders_by_status,
            "avg_order_value": round(avg_order_value, 2),
            "today_orders": today_orders,
            "today_revenue": round(today_revenue, 2),
        }

    async def get_paginated_orders(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
        include_deleted: bool = False,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
    ):
        """Get paginated orders for a workspace"""
        return await self.repo.get_paginated_by_workspace(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=order_by,
            order_direction=order_direction,
            include_deleted=include_deleted,
            start_date=start_date,
            end_date=end_date,
        )
