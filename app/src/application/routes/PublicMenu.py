"""
PublicMenu router — unauthenticated endpoints for QR-menu browsing and order placement.

Full paths (PREFIX = /api/v1/application):
  GET  /api/v1/application/public/menu/{workspace_id}/{persona_id}?table_id=
  POST /api/v1/application/public/orders
  GET  /api/v1/application/public/orders/{order_id}?workspace_id=&persona_id=
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.Customer import CustomerService
from src.application.services.Order import OrderService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import ForbiddenException, GoneException, NotFoundException
from src.models.BillingConfig import BillingConfig
from src.models.Category import Category
from src.models.CustomerSession import CustomerSession
from src.models.Item import Item
from src.models.Persona import Persona
from src.models.Table import Table
from src.models.Workspace import Workspace

router = APIRouter(prefix="/public", tags=["Public Menu"])

# ---------------------------------------------------------------------------
# Default billing config values
# ---------------------------------------------------------------------------

_DEFAULT_BILLING_CONFIG: Dict[str, Any] = {
    "tax_rate": 0.0,
    "tax_label": "Tax",
    "service_charge_rate": 0.0,
    "service_charge_label": "Service Charge",
    "discount_rate": 0.0,
    "currency": "INR",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_active_workspace(workspace_id: int, db: AsyncSession) -> Workspace:
    """Fetch workspace; raise 404 if missing or inactive."""
    stmt = select(Workspace).where(
        and_(Workspace.id == workspace_id, Workspace.is_active.is_(True))
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise NotFoundException("Workspace not found")
    return row


async def _get_active_persona(
    persona_id: int, workspace_id: int, db: AsyncSession
) -> Persona:
    """
    Fetch persona; raise:
      404 if missing / inactive / not in workspace
      410 if deactivated
      403 if closed
    """
    stmt = select(Persona).where(Persona.id == persona_id)
    persona = (await db.execute(stmt)).scalar_one_or_none()

    if not persona or not persona.is_active or persona.workspace_id != workspace_id:
        raise NotFoundException("Persona not found")
    if persona.is_deactivated:
        raise GoneException("This outlet is no longer available")
    if not persona.is_open:
        raise ForbiddenException("closed")
    return persona


async def _get_active_table(
    table_id: int, workspace_id: int, persona_id: int, db: AsyncSession
) -> Table:
    """Fetch table; raise 404 if missing / inactive / wrong scope."""
    stmt = select(Table).where(
        and_(
            Table.id == table_id,
            Table.workspace_id == workspace_id,
            Table.persona_id == persona_id,
            Table.is_active.is_(True),
        )
    )
    table = (await db.execute(stmt)).scalar_one_or_none()
    if not table:
        raise NotFoundException("Table not found")
    return table


async def _get_billing_config(
    workspace_id: int, persona_id: int, db: AsyncSession
) -> Dict[str, Any]:
    """
    Fetch the active BillingConfig for (workspace_id, persona_id).
    Returns a dict with billing fields, falling back to defaults if not found.
    """
    stmt = select(BillingConfig).where(
        and_(
            BillingConfig.workspace_id == workspace_id,
            BillingConfig.persona_id == persona_id,
            BillingConfig.is_active.is_(True),
        )
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        return dict(_DEFAULT_BILLING_CONFIG)
    return {
        "tax_rate": float(row.tax_rate),
        "tax_label": row.tax_label,
        "service_charge_rate": float(row.service_charge_rate),
        "service_charge_label": row.service_charge_label,
        "discount_rate": float(row.discount_rate),
        "currency": row.currency,
    }


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class PublicOrderItemIn(BaseModel):
    item_id: int = Field(..., ge=1)
    quantity: int = Field(1, ge=1)


class PublicCreateOrderRequest(BaseModel):
    workspace_id: int = Field(..., ge=1)
    persona_id: int = Field(..., ge=1)
    table_id: Optional[int] = Field(None, ge=1)
    customer_name: str = Field("Guest", max_length=200)
    customer_phone: Optional[str] = Field(None, max_length=30)
    items: List[PublicOrderItemIn] = Field(..., min_length=1)
    special_instructions: Optional[str] = Field(None, max_length=1000)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/menu/{workspace_id}/{persona_id}", response_model=BaseResponse)
async def get_public_menu(
    workspace_id: int,
    persona_id: int,
    table_id: Optional[int] = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Return the full menu for a persona, optionally scoped to a table.
    No authentication required.
    """
    workspace = await _get_active_workspace(workspace_id, db)
    persona = await _get_active_persona(persona_id, workspace_id, db)

    table_data: Optional[Dict[str, Any]] = None
    if table_id is not None:
        table = await _get_active_table(table_id, workspace_id, persona_id, db)
        table_data = {
            "id": table.id,
            "table_number": table.table_number,
            "capacity": table.capacity,
            "status": table.status,
        }

    # Fetch billing config for this persona
    billing_config = await _get_billing_config(workspace_id, persona_id, db)

    # Fetch available categories
    cat_stmt = select(Category).where(
        and_(
            Category.workspace_id == workspace_id,
            Category.persona_id == persona_id,
            Category.is_active.is_(True),
            Category.is_available.is_(True),
        )
    )
    category_rows = (await db.execute(cat_stmt)).scalars().all()
    category_ids = [c.id for c in category_rows]

    # Fetch available items belonging to those categories
    item_rows: List[Item] = []
    if category_ids:
        item_stmt = select(Item).where(
            and_(
                Item.workspace_id == workspace_id,
                Item.is_active.is_(True),
                Item.is_available.is_(True),
                Item.category_id.in_(category_ids),
            )
        )
        item_rows = (await db.execute(item_stmt)).scalars().all()

    return {
        "success": True,
        "message": "Menu retrieved successfully",
        "data": {
            "workspace": {
                "id": workspace.id,
                "name": workspace.name,
                "description": workspace.description,
            },
            "persona": {
                "id": persona.id,
                "name": persona.name,
                "description": persona.description,
                "is_open": persona.is_open,
                "logo_url": persona.logo_url,
                "address": persona.address,
                "phone": persona.phone,
            },
            "table": table_data,
            "billing_config": billing_config,
            "categories": [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "is_available": c.is_available,
                }
                for c in category_rows
            ],
            "items": [
                {
                    "id": i.id,
                    "name": i.name,
                    "description": i.description,
                    "price": float(i.price),
                    "is_available": i.is_available,
                    "is_vegetarian": i.is_vegetarian,
                    "category_id": i.category_id,
                    "image_url": i.image_url,
                }
                for i in item_rows
            ],
        },
    }


@router.post("/orders", response_model=BaseResponse, status_code=201)
async def create_public_order(
    request: PublicCreateOrderRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Place an order from the public menu. No authentication required.
    Computes tax and service charge from BillingConfig, then creates a
    CustomerSession linking the customer to the placed order.
    """
    await _get_active_workspace(request.workspace_id, db)
    await _get_active_persona(request.persona_id, request.workspace_id, db)

    if request.table_id is not None:
        await _get_active_table(request.table_id, request.workspace_id, request.persona_id, db)

    # Resolve billing rates for this persona
    billing_config = await _get_billing_config(request.workspace_id, request.persona_id, db)
    tax_rate: float = billing_config["tax_rate"]
    service_charge_rate: float = billing_config["service_charge_rate"]

    # Compute subtotal from requested items so we can derive tax/service charge.
    # We fetch item prices directly to avoid a round-trip through OrderService internals.
    item_ids = [item.item_id for item in request.items]
    item_stmt = select(Item).where(
        and_(
            Item.id.in_(item_ids),
            Item.workspace_id == request.workspace_id,
            Item.is_active.is_(True),
        )
    )
    item_price_map: Dict[int, float] = {
        row.id: float(row.price)
        for row in (await db.execute(item_stmt)).scalars().all()
    }

    subtotal: float = sum(
        item_price_map.get(item.item_id, 0.0) * item.quantity
        for item in request.items
    )
    tax_amount: float = round(subtotal * tax_rate, 2)
    service_charge: float = round(subtotal * service_charge_rate, 2)

    # Build order payload
    order_service = OrderService(db)
    data: Dict[str, Any] = {
        "workspace_id": request.workspace_id,
        "persona_id": request.persona_id,
        "order_type": "dine_in",
        "customer_name": request.customer_name,
        "table_id": request.table_id,
        "special_instructions": request.special_instructions,
        "is_active": True,
        "items": [item.model_dump() for item in request.items],
        "tax_amount": tax_amount,
        "service_charge": service_charge,
    }

    try:
        order = await order_service.create_order(data)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(exc))

    # Look up or create the customer, then record a CustomerSession
    if request.customer_phone:
        customer_service = CustomerService(db)
        customer = await customer_service.create_or_get_customer(
            name=request.customer_name,
            mobile=request.customer_phone,
            workspace_id=request.workspace_id,
            persona_id=request.persona_id,
        )
        customer_id: int = customer["id"]

        session_record = CustomerSession(
            workspace_id=request.workspace_id,
            persona_id=request.persona_id,
            customer_id=customer_id,
            order_id=order["order_id"],
            table_id=request.table_id,
            customer_name=request.customer_name,
            customer_phone=request.customer_phone,
            session_token=uuid.uuid4().hex,
            is_active=True,
        )
        db.add(session_record)
        await db.flush()

    return {"success": True, "message": "Order placed successfully", "data": order}


@router.get("/orders/{order_id}", response_model=BaseResponse)
async def get_public_order(
    order_id: str,
    workspace_id: int = Query(..., ge=1),
    persona_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retrieve a single order with its line items. No authentication required.
    """
    service = OrderService(db)
    order = await service.get_order_with_items(order_id, workspace_id, persona_id)
    if not order:
        raise NotFoundException("Order not found")
    return {"success": True, "message": "Order retrieved successfully", "data": order}