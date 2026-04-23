"""
OrderService — business logic for orders (order_details + order line items).
"""

import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.models.Item import Item
from src.models.Order import Order
from src.models.OrderDetail import OrderDetail
from src.repositories.OrderRepository import OrderDetailRepository, OrderRepository


def generate_order_id(workspace_id: int) -> str:
    """Generate a unique order_id: ORD-{workspace_id}-{timestamp}-{token}."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    token = secrets.token_hex(4)
    return f"ORD-{workspace_id}-{timestamp}-{token}"


class OrderService:
    """Service for managing orders."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.detail_repo = OrderDetailRepository(db)
        self.order_repo = OrderRepository(db)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_order(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atomically create an order_details record + one orders row per line item.

        Expected data keys:
            workspace_id, persona_id, order_type, customer_id (opt),
            customer_name, table_id (opt), area_id (opt), currency (opt),
            special_instructions (opt), created_by (opt),
            tax_amount (opt), service_charge (opt), discount_amount (opt),
            items: list of {item_id, quantity}
        """
        order_id = generate_order_id(data["workspace_id"])

        # Fetch item prices from DB
        item_ids = [i["item_id"] for i in data.get("items", [])]
        price_map: Dict[int, Dict[str, Any]] = {}
        if item_ids:
            stmt = select(Item).where(
                Item.id.in_(item_ids),
                Item.is_active == True,  # noqa: E712
            )
            result = await self.db.execute(stmt)
            for row in result.scalars().all():
                price_map[row.id] = {"price": row.price, "name": row.name}

        # Build line items
        line_items: List[Dict[str, Any]] = []
        subtotal = Decimal("0.00")
        for entry in data.get("items", []):
            item_id = entry["item_id"]
            quantity = int(entry.get("quantity", 1))
            item_info = price_map.get(item_id)
            if not item_info:
                raise ValueError(f"Item {item_id} not found or inactive")
            unit_price = Decimal(str(item_info["price"]))
            line_total = unit_price * quantity
            subtotal += line_total
            line_items.append({
                "order_id": order_id,
                "item_id": item_id,
                "item_name": item_info["name"],
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
                "workspace_id": data["workspace_id"],
                "persona_id": data["persona_id"],
                "is_active": True,
            })

        tax_amount = Decimal(str(data.get("tax_amount", "0.00")))
        service_charge = Decimal(str(data.get("service_charge", "0.00")))
        discount_amount = Decimal(str(data.get("discount_amount", "0.00")))
        total_amount = subtotal + tax_amount + service_charge - discount_amount

        # Create order_details
        detail_payload = {
            "order_id": order_id,
            "order_type": data.get("order_type", "dine_in"),
            "status": "pending",
            "customer_id": data.get("customer_id"),
            "customer_name": data.get("customer_name", ""),
            "table_id": data.get("table_id"),
            "area_id": data.get("area_id"),
            "subtotal": subtotal,
            "tax_amount": tax_amount,
            "service_charge": service_charge,
            "discount_amount": discount_amount,
            "total_amount": total_amount,
            "currency": data.get("currency", "INR"),
            "special_instructions": data.get("special_instructions"),
            "workspace_id": data["workspace_id"],
            "persona_id": data["persona_id"],
            "created_by": data.get("created_by"),
            "is_active": True,
        }
        order_detail = await self.detail_repo.create(detail_payload)

        # Bulk-create line items
        created_items: List[Dict[str, Any]] = []
        if line_items:
            created_items = await self.order_repo.bulk_create(line_items)

        order_detail["items"] = created_items
        return order_detail

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_order_with_items(
        self, order_id: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch order_details + all orders rows for that order_id."""
        detail = await self.detail_repo.get_by_order_id(order_id)
        if not detail:
            return None
        items = await self.order_repo.get_by_order_id(order_id)
        detail["items"] = items
        return detail

    async def get_paginated_orders(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated order_details with optional filters."""
        conditions = [
            OrderDetail.workspace_id == workspace_id,
            OrderDetail.is_active == True,  # noqa: E712
        ]
        if persona_id is not None:
            conditions.append(OrderDetail.persona_id == persona_id)
        if status is not None:
            conditions.append(OrderDetail.status == status)
        if start_date is not None:
            conditions.append(OrderDetail.created_at >= start_date)
        if end_date is not None:
            conditions.append(OrderDetail.created_at <= end_date)

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

    async def get_order_items(self, order_id: str) -> List[Dict[str, Any]]:
        """Return all line items for an order."""
        return await self.order_repo.get_by_order_id(order_id)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_order_status(self, order_id: str, status: str) -> bool:
        """Update order_details.status by order_id string."""
        detail = await self.detail_repo.get_by_order_id(order_id)
        if not detail:
            return False
        return await self.detail_repo.update(detail["id"], {"status": status})

    async def cancel_order(self, order_id: str) -> bool:
        """Set order status to cancelled."""
        return await self.update_order_status(order_id, "cancelled")

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    async def get_order_statistics(
        self,
        workspace_id: int,
        persona_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Aggregate order statistics for a workspace."""
        today = datetime.now(timezone.utc).date()

        base_conditions = [
            OrderDetail.workspace_id == workspace_id,
            OrderDetail.is_active == True,  # noqa: E712
        ]
        if persona_id is not None:
            base_conditions.append(OrderDetail.persona_id == persona_id)
        if start_date is not None:
            base_conditions.append(OrderDetail.created_at >= start_date)
        if end_date is not None:
            base_conditions.append(OrderDetail.created_at <= end_date)

        where_expr = and_(*base_conditions)

        # Total orders + revenue + avg
        agg_stmt = select(
            func.count(OrderDetail.id).label("total_orders"),
            func.coalesce(func.sum(OrderDetail.total_amount), 0).label("total_revenue"),
            func.coalesce(func.avg(OrderDetail.total_amount), 0).label("avg_order_value"),
        ).where(where_expr)
        agg_row = (await self.db.execute(agg_stmt)).one()

        # Orders by status
        status_stmt = select(
            func.count(case((OrderDetail.status == "pending", 1))).label("pending"),
            func.count(case((OrderDetail.status == "confirmed", 1))).label("confirmed"),
            func.count(case((OrderDetail.status == "preparing", 1))).label("preparing"),
            func.count(case((OrderDetail.status == "ready", 1))).label("ready"),
            func.count(case((OrderDetail.status == "served", 1))).label("served"),
            func.count(case((OrderDetail.status == "cancelled", 1))).label("cancelled"),
        ).where(where_expr)
        status_row = (await self.db.execute(status_stmt)).one()

        # Orders by type
        type_stmt = select(
            func.count(case((OrderDetail.order_type == "dine_in", 1))).label("dine_in"),
            func.count(case((OrderDetail.order_type == "takeaway", 1))).label("takeaway"),
            func.count(case((OrderDetail.order_type == "delivery", 1))).label("delivery"),
        ).where(where_expr)
        type_row = (await self.db.execute(type_stmt)).one()

        # Today's orders + revenue
        today_conditions = [
            OrderDetail.workspace_id == workspace_id,
            OrderDetail.is_active == True,  # noqa: E712
            func.date(OrderDetail.created_at) == today,
        ]
        if persona_id is not None:
            today_conditions.append(OrderDetail.persona_id == persona_id)

        today_stmt = select(
            func.count(OrderDetail.id).label("today_orders"),
            func.coalesce(func.sum(OrderDetail.total_amount), 0).label("today_revenue"),
        ).where(and_(*today_conditions))
        today_row = (await self.db.execute(today_stmt)).one()

        return {
            "total_orders": agg_row.total_orders,
            "total_revenue": float(agg_row.total_revenue),
            "avg_order_value": float(agg_row.avg_order_value),
            "orders_by_status": {
                "pending": status_row.pending,
                "confirmed": status_row.confirmed,
                "preparing": status_row.preparing,
                "ready": status_row.ready,
                "served": status_row.served,
                "cancelled": status_row.cancelled,
            },
            "orders_by_type": {
                "dine_in": type_row.dine_in,
                "takeaway": type_row.takeaway,
                "delivery": type_row.delivery,
            },
            "today_orders": today_row.today_orders,
            "today_revenue": float(today_row.today_revenue),
        }
