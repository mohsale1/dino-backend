"""
PublicMenu router — unauthenticated endpoints for QR-menu browsing and order placement.

Full paths (PREFIX = /api/v1/application):
  GET  /api/v1/application/public/menu/{workspace_id}/{persona_id}?table_id=
  POST /api/v1/application/public/orders
  GET  /api/v1/application/public/orders/{order_id}?workspace_id=&persona_id=
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.Customer import CustomerService
from src.application.services.Order import OrderService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError, PermissionDeniedError, ResourceGoneError
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
# Internal helpers — each fetches only the columns it needs
# ---------------------------------------------------------------------------

async def _get_active_workspace(workspace_id: int, db: AsyncSession) -> Tuple[int, str, Optional[str]]:
    """Return (id, name, description); raise 404 if missing or inactive."""
    stmt = (
        select(Workspace.id, Workspace.name, Workspace.description)
        .where(Workspace.id == workspace_id, Workspace.is_active.is_(True))
    )
    row = (await db.execute(stmt)).one_or_none()
    if not row:
        raise NotFoundError("Workspace not found")
    return row


async def _get_active_persona(persona_id: int, db: AsyncSession) -> Persona:
    """
    Fetch persona columns needed for response + status checks.
    Raises 404 / 410 / 403 as appropriate.
    """
    stmt = select(
        Persona.id,
        Persona.name,
        Persona.description,
        Persona.logo_url,
        Persona.address,
        Persona.phone,
        Persona.is_open,
        Persona.is_active,
        Persona.is_deactivated,
    ).where(Persona.id == persona_id)
    row = (await db.execute(stmt)).one_or_none()

    if not row or not row.is_active:
        raise NotFoundError("Persona not found")
    if row.is_deactivated:
        raise ResourceGoneError("This outlet is no longer available")
    if not row.is_open:
        raise PermissionDeniedError("This outlet is currently closed")
    return row


async def _get_active_table(table_id: int, persona_id: int, db: AsyncSession) -> Any:
    """Fetch only the table columns needed for the response."""
    stmt = select(
        Table.id,
        Table.table_number,
        Table.capacity,
        Table.status,
    ).where(
        Table.id == table_id,
        Table.persona_id == persona_id,
        Table.is_active.is_(True),
    )
    row = (await db.execute(stmt)).one_or_none()
    if not row:
        raise NotFoundError("Table not found")
    return row


async def _get_billing_config(workspace_id: int, persona_id: int, db: AsyncSession) -> Dict[str, Any]:
    """Fetch BillingConfig; fall back to defaults if not found."""
    stmt = select(
        BillingConfig.tax_rate,
        BillingConfig.tax_label,
        BillingConfig.service_charge_rate,
        BillingConfig.service_charge_label,
        BillingConfig.discount_rate,
        BillingConfig.currency,
    ).where(
        BillingConfig.workspace_id == workspace_id,
        BillingConfig.persona_id == persona_id,
        BillingConfig.is_active.is_(True),
    )
    row = (await db.execute(stmt)).one_or_none()
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


async def _get_menu_data(
    persona_id: int, db: AsyncSession
) -> Tuple[List[Any], List[Any]]:
    """Fetch categories and items for a persona in parallel."""

    async def _categories() -> List[Any]:
        stmt = select(
            Category.id,
            Category.name,
            Category.description,
            Category.is_available,
        ).where(
            Category.persona_id == persona_id,
            Category.is_active.is_(True),
            Category.is_available.is_(True),
        )
        return (await db.execute(stmt)).all()

    async def _items(category_ids: List[int]) -> List[Any]:
        if not category_ids:
            return []
        stmt = select(
            Item.id,
            Item.name,
            Item.description,
            Item.price,
            Item.is_available,
            Item.is_vegetarian,
            Item.category_id,
            Item.image_url,
        ).where(
            Item.persona_id == persona_id,
            Item.is_active.is_(True),
            Item.is_available.is_(True),
            Item.category_id.in_(category_ids),
        )
        return (await db.execute(stmt)).all()

    cats = await _categories()
    items = await _items([c.id for c in cats])
    return cats, items


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
    Return the full menu for a persona.
    Workspace, persona, billing config, and menu data are fetched in parallel.
    Table is fetched only when table_id is provided.
    """
    # Validate workspace + persona + billing + menu data in parallel
    results = await asyncio.gather(
        _get_active_workspace(workspace_id, db),
        _get_active_persona(persona_id, db),
        _get_billing_config(workspace_id, persona_id, db),
        _get_menu_data(persona_id, db),
    )
    workspace_row, persona_row, billing_config, (category_rows, item_rows) = results

    # Table is conditional — fetch only if requested
    table_data: Optional[Dict[str, Any]] = None
    if table_id is not None:
        t = await _get_active_table(table_id, persona_id, db)
        table_data = {
            "id": t.id,
            "table_number": t.table_number,
            "capacity": t.capacity,
            "status": t.status,
        }

    return {
        "success": True,
        "message": "Menu retrieved successfully",
        "data": {
            "workspace": {
                "id": workspace_row.id,
                "name": workspace_row.name,
                "description": workspace_row.description,
            },
            "persona": {
                "id": persona_row.id,
                "name": persona_row.name,
                "description": persona_row.description,
                "is_open": persona_row.is_open,
                "logo_url": persona_row.logo_url,
                "address": persona_row.address,
                "phone": persona_row.phone,
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
    Validation, billing config, and item price fetch run in parallel.
    """
    # Validate workspace + persona + billing config in parallel
    _, _, billing_config = await asyncio.gather(
        _get_active_workspace(request.workspace_id, db),
        _get_active_persona(request.persona_id, db),
        _get_billing_config(request.workspace_id, request.persona_id, db),
    )

    # Validate table if provided
    if request.table_id is not None:
        await _get_active_table(request.table_id, request.persona_id, db)

    tax_rate: float = billing_config["tax_rate"]
    service_charge_rate: float = billing_config["service_charge_rate"]

    # Fetch only id + price for the requested items — minimal columns
    item_ids = [item.item_id for item in request.items]
    price_rows = (
        await db.execute(
            select(Item.id, Item.price).where(
                Item.id.in_(item_ids),
                Item.persona_id == request.persona_id,
                Item.is_active.is_(True),
            )
        )
    ).all()
    item_price_map: Dict[int, float] = {r.id: float(r.price) for r in price_rows}

    subtotal: float = sum(
        item_price_map.get(item.item_id, 0.0) * item.quantity
        for item in request.items
    )
    tax_amount: float = round(subtotal * tax_rate, 2)
    service_charge: float = round(subtotal * service_charge_rate, 2)

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
        order = await OrderService(db).create_order(data)
    except ValueError as exc:
        raise BadRequestError(str(exc))

    # Create customer + session record if phone provided
    if request.customer_phone:
        customer = await CustomerService(db).create_or_get_customer(
            name=request.customer_name,
            mobile=request.customer_phone,
        )
        db.add(CustomerSession(
            workspace_id=request.workspace_id,
            persona_id=request.persona_id,
            customer_id=customer["id"],
            order_id=order["order_id"],
            table_id=request.table_id,
            customer_name=request.customer_name,
            customer_phone=request.customer_phone,
            session_token=uuid.uuid4().hex,
            is_active=True,
        ))
        await db.flush()

    return {"success": True, "message": "Order placed successfully", "data": order}


@router.get("/orders/{order_id}", response_model=BaseResponse)
async def get_public_order(
    order_id: str,
    workspace_id: int = Query(..., ge=1),
    persona_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve a single order with its line items. No authentication required."""
    order = await OrderService(db).get_order_with_items(order_id, workspace_id, persona_id)
    if not order:
        raise NotFoundError("Order not found")
    return {"success": True, "message": "Order retrieved successfully", "data": order}