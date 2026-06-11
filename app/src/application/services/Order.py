"""
OrderService — business logic for orders (order_details + order line items).
"""

import asyncio
import logging
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, cast, func, select, Date
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.core.Exceptions import ItemNotFoundOrInactiveError, NoItemsInOrderError
from src.models.Item import Item
from src.models.Order import Order
from src.models.OrderDetail import OrderDetail
from src.repositories.OrderRepository import OrderDetailRepository, OrderRepository

logger = logging.getLogger(__name__)


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

        Raises
        ------
        NoItemsInOrderError
            If the items list is empty.
        ItemNotFoundOrInactiveError
            If any item_id is not found or inactive for this persona.
        """
        if not data.get("items"):
            raise NoItemsInOrderError()

        order_id = generate_order_id(data["workspace_id"])
        item_ids = [i["item_id"] for i in data["items"]]

        logger.debug(
            "order.create.fetching_items order_id=%s persona_id=%s item_ids=%s",
            order_id, data["persona_id"], item_ids,
        )

        # Fetch all item prices in one query
        stmt = select(Item).where(
            Item.id.in_(item_ids),
            Item.persona_id == data["persona_id"],
            Item.is_active.is_(True),
        )
        price_map: Dict[int, Dict[str, Any]] = {
            row.id: {"price": row.price, "name": row.name}
            for row in (await self.db.execute(stmt)).scalars().all()
        }

        # Build line items — raise immediately on any missing item
        line_items: List[Dict[str, Any]] = []
        subtotal = Decimal("0.00")
        for entry in data["items"]:
            item_id = entry["item_id"]
            quantity = int(entry.get("quantity", 1))
            item_info = price_map.get(item_id)
            if not item_info:
                logger.warning(
                    "order.create.item_not_found order_id=%s item_id=%s persona_id=%s",
                    order_id, item_id, data["persona_id"],
                )
                raise ItemNotFoundOrInactiveError(
                    f"Item {item_id} not found or inactive for this persona"
                )
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

        tax_amount = Decimal(str(data.get("tax_amount") or "0.00"))
        service_charge = Decimal(str(data.get("service_charge") or "0.00"))
        discount_amount = Decimal(str(data.get("discount_amount") or "0.00"))
        total_amount = subtotal + tax_amount + service_charge - discount_amount

        detail_payload = {
            "order_id": order_id,
            "order_type": data.get("order_type", "dine_in"),
            "status": "pending",
            "customer_id": data.get("customer_id"),
            "customer_name": data.get("customer_name", "Guest"),
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

        async with self.db.begin_nested():
            order_detail = await self.detail_repo.create(detail_payload)
            created_items = await self.order_repo.bulk_create(line_items)

        order_detail["items"] = created_items
        logger.info(
            "order.created order_id=%s workspace_id=%s persona_id=%s "
            "items=%s subtotal=%s total=%s",
            order_id, data["workspace_id"], data["persona_id"],
            len(created_items), float(subtotal), float(total_amount),
        )
        return order_detail

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_order_with_items(
        self,
        order_id: str,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch order_details + all line items scoped to workspace and persona."""
        detail = await self.detail_repo.get_by_order_id_for_persona(
            order_id, workspace_id, persona_id
        )
        if not detail:
            return None
        items = await self.order_repo.get_by_order_id(order_id)
        detail["items"] = items
        logger.debug(
            "order.get order_id=%s workspace_id=%s persona_id=%s items=%s",
            order_id, workspace_id, persona_id, len(items),
        )
        return detail

    async def get_order_status(
        self,
        order_id: str,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[str]:
        """Lightweight fetch — returns only the status string, no line items."""
        stmt = (
            select(OrderDetail.status)
            .where(
                OrderDetail.order_id == order_id,
                OrderDetail.workspace_id == workspace_id,
                OrderDetail.persona_id == persona_id,
                OrderDetail.is_active.is_(True),
            )
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_paginated_orders(
        self,
        workspace_id: int,
        persona_id: int,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated order_details with optional filters, scoped to persona."""
        conditions = [
            OrderDetail.workspace_id == workspace_id,
            OrderDetail.persona_id == persona_id,
            OrderDetail.is_active.is_(True),
        ]
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

        result = []
        for idx, row in enumerate(rows, start=offset + 1):
            d = row_to_dict(row)
            d["index"] = idx
            result.append(d)

        logger.debug(
            "order.list workspace_id=%s persona_id=%s status=%s total=%s returned=%s page=%s",
            workspace_id, persona_id, status, total, len(result), page,
        )
        return result, total, total_pages

    async def get_order_items(self, order_id: str) -> List[Dict[str, Any]]:
        """Return all line items for an order."""
        return await self.order_repo.get_by_order_id(order_id)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_order_status(
        self,
        order_id: str,
        workspace_id: int,
        persona_id: int,
        status: str,
    ) -> bool:
        """Single-query UPDATE of order status scoped to workspace and persona."""
        updated = await self.detail_repo.update_status_for_persona(
            order_id, workspace_id, persona_id, status
        )
        if updated:
            logger.info(
                "order.status.updated order_id=%s workspace_id=%s persona_id=%s status=%s",
                order_id, workspace_id, persona_id, status,
            )
        return updated

    async def cancel_order(
        self,
        order_id: str,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Set order status to cancelled."""
        updated = await self.update_order_status(order_id, workspace_id, persona_id, "cancelled")
        if updated:
            logger.info(
                "order.cancelled order_id=%s workspace_id=%s persona_id=%s",
                order_id, workspace_id, persona_id,
            )
        return updated

    # ------------------------------------------------------------------
    # Statistics — all queries parallelised
    # ------------------------------------------------------------------

    async def get_order_statistics(
        self,
        workspace_id: int,
        persona_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Aggregate order statistics — 4 queries run in parallel."""
        today = datetime.now(timezone.utc).date()

        base = [
            OrderDetail.workspace_id == workspace_id,
            OrderDetail.persona_id == persona_id,
            OrderDetail.is_active.is_(True),
        ]
        if start_date is not None:
            base.append(OrderDetail.created_at >= start_date)
        if end_date is not None:
            base.append(OrderDetail.created_at <= end_date)

        where_expr = and_(*base)

        async def _aggregates():
            stmt = select(
                func.count(OrderDetail.id).label("total_orders"),
                func.coalesce(func.sum(OrderDetail.total_amount), 0).label("total_revenue"),
                func.coalesce(func.avg(OrderDetail.total_amount), 0).label("avg_order_value"),
            ).where(where_expr)
            return (await self.db.execute(stmt)).one()

        async def _by_status():
            stmt = select(
                func.count(case((OrderDetail.status == "pending", 1))).label("pending"),
                func.count(case((OrderDetail.status == "confirmed", 1))).label("confirmed"),
                func.count(case((OrderDetail.status == "preparing", 1))).label("preparing"),
                func.count(case((OrderDetail.status == "ready", 1))).label("ready"),
                func.count(case((OrderDetail.status == "served", 1))).label("served"),
                func.count(case((OrderDetail.status == "completed", 1))).label("completed"),
                func.count(case((OrderDetail.status == "cancelled", 1))).label("cancelled"),
            ).where(where_expr)
            return (await self.db.execute(stmt)).one()

        async def _by_type():
            stmt = select(
                func.count(case((OrderDetail.order_type == "dine_in", 1))).label("dine_in"),
                func.count(case((OrderDetail.order_type == "takeaway", 1))).label("takeaway"),
                func.count(case((OrderDetail.order_type == "delivery", 1))).label("delivery"),
            ).where(where_expr)
            return (await self.db.execute(stmt)).one()

        async def _today():
            stmt = select(
                func.count(OrderDetail.id).label("today_orders"),
                func.coalesce(func.sum(OrderDetail.total_amount), 0).label("today_revenue"),
            ).where(
                and_(
                    OrderDetail.workspace_id == workspace_id,
                    OrderDetail.persona_id == persona_id,
                    OrderDetail.is_active.is_(True),
                    cast(OrderDetail.created_at, Date) == today,
                )
            )
            return (await self.db.execute(stmt)).one()

        agg_row, status_row, type_row, today_row = await asyncio.gather(
            _aggregates(), _by_status(), _by_type(), _today()
        )

        logger.debug(
            "order.statistics workspace_id=%s persona_id=%s total_orders=%s total_revenue=%s",
            workspace_id, persona_id, agg_row.total_orders, float(agg_row.total_revenue),
        )
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
                "completed": status_row.completed,
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
