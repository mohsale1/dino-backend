"""
Orders router — CRUD for order_details, order line items, and transactions.
All endpoints are authenticated. workspace_id is resolved from the JWT.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Order import OrderService
from src.application.services.OrderTransaction import OrderTransactionService
from src.application.services.Persona import PersonaService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import (
    BadRequestError,
    CannotCancelOrderError,
    NotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_workspace(current_user: Dict[str, Any]) -> int:
    wid = current_user.get("workspace_id")
    if not wid:
        raise BadRequestError("workspace_id could not be resolved for this user")
    return wid


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class OrderItemIn(BaseModel):
    item_id: int = Field(..., ge=1)
    quantity: int = Field(1, ge=1)


class CreateOrderRequest(BaseModel):
    persona_id: int = Field(..., ge=1)
    order_type: Literal["dine_in", "takeaway", "delivery"] = "dine_in"
    customer_id: Optional[int] = None
    customer_name: str = Field("Guest", max_length=200)
    table_id: Optional[int] = None
    area_id: Optional[int] = None
    currency: str = Field("INR", max_length=10)
    special_instructions: Optional[str] = Field(None, max_length=1000)
    tax_amount: float = Field(0.0, ge=0)
    service_charge: float = Field(0.0, ge=0)
    discount_amount: float = Field(0.0, ge=0)
    items: List[OrderItemIn] = Field(..., min_length=1)


class UpdateStatusRequest(BaseModel):
    status: Literal["pending", "confirmed", "preparing", "ready", "served", "completed", "cancelled"]


class CreateTransactionRequest(BaseModel):
    customer_id: Optional[int] = None
    paid_amount: float = Field(0.0, ge=0)
    total_amount: float = Field(..., ge=0)
    currency: str = Field("INR", max_length=10)
    payment_method: Optional[str] = Field(None, max_length=50)
    payment_status: Literal["unpaid", "partial", "paid", "refunded"] = "unpaid"
    payment_ref: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=500)


class UpdateTransactionRequest(BaseModel):
    paid_amount: Optional[float] = Field(None, ge=0)
    total_amount: Optional[float] = Field(None, ge=0)
    payment_method: Optional[str] = Field(None, max_length=50)
    payment_status: Optional[Literal["unpaid", "partial", "paid", "refunded"]] = None
    payment_ref: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=500)


# ---------------------------------------------------------------------------
# POST /orders
# ---------------------------------------------------------------------------

@router.post("", response_model=BaseResponse, status_code=201)
async def create_order(
    request: CreateOrderRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Create a new order with line items atomically."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "orders.create.request user_id=%s workspace_id=%s persona_id=%s "
        "order_type=%s items=%s customer=%r",
        user_id, workspace_id, request.persona_id,
        request.order_type, len(request.items), request.customer_name,
    )

    persona = await PersonaService(db).get_by_id(request.persona_id)
    if not persona:
        logger.warning(
            "orders.create.persona_not_found user_id=%s persona_id=%s",
            user_id, request.persona_id,
        )
        raise NotFoundError("Persona not found")

    data = request.model_dump()
    data["workspace_id"] = workspace_id
    data["created_by"] = user_id

    order = await OrderService(db).create_order(data)

    logger.info(
        "orders.create.response user_id=%s workspace_id=%s persona_id=%s "
        "order_id=%s total=%s",
        user_id, workspace_id, request.persona_id,
        order.get("order_id"), order.get("total_amount"),
    )
    return {"success": True, "message": "Order created successfully", "data": order}


# ---------------------------------------------------------------------------
# GET /orders
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_orders(
    persona_id: int = Query(..., ge=1),
    order_status: Optional[Literal["pending", "confirmed", "preparing", "ready", "served", "completed", "cancelled"]] = Query(None, alias="status"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated order list scoped to workspace and persona."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "orders.list.request user_id=%s workspace_id=%s persona_id=%s "
        "status=%s start=%s end=%s page=%s page_size=%s",
        user_id, workspace_id, persona_id,
        order_status, start_date, end_date, page, page_size,
    )

    items, total, total_pages = await OrderService(db).get_paginated_orders(
        workspace_id=workspace_id,
        persona_id=persona_id,
        status=order_status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    logger.info(
        "orders.list.response user_id=%s workspace_id=%s persona_id=%s "
        "total=%s page=%s total_pages=%s returned=%s",
        user_id, workspace_id, persona_id, total, page, total_pages, len(items),
    )
    return {
        "success": True,
        "message": "Orders retrieved successfully",
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


# ---------------------------------------------------------------------------
# GET /orders/statistics
# ---------------------------------------------------------------------------

@router.get("/statistics", response_model=BaseResponse)
async def get_order_statistics(
    persona_id: int = Query(..., ge=1),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated order statistics — all queries parallelised."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "orders.statistics.request user_id=%s workspace_id=%s persona_id=%s "
        "start=%s end=%s",
        user_id, workspace_id, persona_id, start_date, end_date,
    )

    stats = await OrderService(db).get_order_statistics(
        workspace_id=workspace_id,
        persona_id=persona_id,
        start_date=start_date,
        end_date=end_date,
    )

    logger.info(
        "orders.statistics.response user_id=%s workspace_id=%s persona_id=%s "
        "total_orders=%s total_revenue=%s",
        user_id, workspace_id, persona_id,
        stats.get("total_orders"), stats.get("total_revenue"),
    )
    return {"success": True, "message": "Statistics retrieved successfully", "data": stats}


# ---------------------------------------------------------------------------
# GET /orders/transactions
# ---------------------------------------------------------------------------

@router.get("/transactions", response_model=BaseResponse)
async def get_transactions(
    persona_id: int = Query(..., ge=1),
    payment_status: Optional[Literal["unpaid", "partial", "paid", "refunded"]] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated payment transactions scoped to workspace and persona."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "orders.transactions.list.request user_id=%s workspace_id=%s persona_id=%s "
        "payment_status=%s page=%s page_size=%s",
        user_id, workspace_id, persona_id, payment_status, page, page_size,
    )

    items, total, total_pages = await OrderTransactionService(db).get_paginated_transactions(
        workspace_id=workspace_id,
        persona_id=persona_id,
        payment_status=payment_status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    logger.info(
        "orders.transactions.list.response user_id=%s workspace_id=%s persona_id=%s "
        "total=%s page=%s returned=%s",
        user_id, workspace_id, persona_id, total, page, len(items),
    )
    return {
        "success": True,
        "message": "Transactions retrieved successfully",
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


# ---------------------------------------------------------------------------
# PUT /orders/transactions/{transaction_id}
# ---------------------------------------------------------------------------

@router.put("/transactions/{transaction_id}", response_model=BaseResponse)
async def update_transaction(
    transaction_id: int,
    request: UpdateTransactionRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update a payment transaction scoped to workspace and persona."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    data = request.model_dump(exclude_unset=True)

    if not data:
        logger.warning(
            "orders.transaction.update.empty_payload user_id=%s transaction_id=%s",
            user_id, transaction_id,
        )
        raise BadRequestError("No fields provided to update")

    logger.info(
        "orders.transaction.update.request user_id=%s workspace_id=%s "
        "persona_id=%s transaction_id=%s fields=%s",
        user_id, workspace_id, persona_id, transaction_id, list(data.keys()),
    )

    success = await OrderTransactionService(db).update_transaction(
        transaction_id, workspace_id, persona_id, data
    )
    if not success:
        raise NotFoundError("Transaction not found")

    logger.info(
        "orders.transaction.update.response user_id=%s transaction_id=%s fields=%s",
        user_id, transaction_id, list(data.keys()),
    )
    return {"success": True, "message": "Transaction updated successfully"}


# ---------------------------------------------------------------------------
# GET /orders/{order_id}
# ---------------------------------------------------------------------------

@router.get("/{order_id}", response_model=BaseResponse)
async def get_order(
    order_id: str,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a single order with its line items."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "orders.get.request user_id=%s workspace_id=%s persona_id=%s order_id=%s",
        user_id, workspace_id, persona_id, order_id,
    )

    order = await OrderService(db).get_order_with_items(order_id, workspace_id, persona_id)
    if not order:
        logger.warning(
            "orders.get.not_found user_id=%s workspace_id=%s persona_id=%s order_id=%s",
            user_id, workspace_id, persona_id, order_id,
        )
        raise NotFoundError("Order not found")

    logger.info(
        "orders.get.response user_id=%s order_id=%s status=%s items=%s",
        user_id, order_id, order.get("status"), len(order.get("items", [])),
    )
    return {"success": True, "message": "Order retrieved successfully", "data": order}


# ---------------------------------------------------------------------------
# PUT /orders/{order_id}/status
# ---------------------------------------------------------------------------

@router.put("/{order_id}/status", response_model=BaseResponse)
async def update_order_status(
    order_id: str,
    request: UpdateStatusRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update the status of an order — single round-trip UPDATE."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "orders.status.update.request user_id=%s workspace_id=%s "
        "persona_id=%s order_id=%s new_status=%s",
        user_id, workspace_id, persona_id, order_id, request.status,
    )

    success = await OrderService(db).update_order_status(
        order_id, workspace_id, persona_id, request.status
    )
    if not success:
        logger.warning(
            "orders.status.update.not_found user_id=%s order_id=%s",
            user_id, order_id,
        )
        raise NotFoundError("Order not found")

    logger.info(
        "orders.status.update.response user_id=%s order_id=%s status=%s",
        user_id, order_id, request.status,
    )
    return {"success": True, "message": "Order status updated successfully"}


# ---------------------------------------------------------------------------
# PUT /orders/{order_id}/cancel
# ---------------------------------------------------------------------------

@router.put("/{order_id}/cancel", response_model=BaseResponse)
async def cancel_order(
    order_id: str,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an order — lightweight status check, then single UPDATE."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "orders.cancel.request user_id=%s workspace_id=%s persona_id=%s order_id=%s",
        user_id, workspace_id, persona_id, order_id,
    )

    # Lightweight status-only fetch — no line items loaded
    current_status = await OrderService(db).get_order_status(order_id, workspace_id, persona_id)
    if current_status is None:
        logger.warning(
            "orders.cancel.not_found user_id=%s order_id=%s",
            user_id, order_id,
        )
        raise NotFoundError("Order not found")

    if current_status in ("cancelled", "served", "completed"):
        logger.warning(
            "orders.cancel.terminal_state user_id=%s order_id=%s status=%s",
            user_id, order_id, current_status,
        )
        raise CannotCancelOrderError(
            f"Cannot cancel an order that is already '{current_status}'"
        )

    await OrderService(db).cancel_order(order_id, workspace_id, persona_id)

    logger.info(
        "orders.cancel.response user_id=%s order_id=%s workspace_id=%s",
        user_id, order_id, workspace_id,
    )
    return {"success": True, "message": "Order cancelled successfully"}


# ---------------------------------------------------------------------------
# GET /orders/{order_id}/items
# ---------------------------------------------------------------------------

@router.get("/{order_id}/items", response_model=BaseResponse)
async def get_order_items(
    order_id: str,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get all line items for an order."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "orders.items.request user_id=%s workspace_id=%s persona_id=%s order_id=%s",
        user_id, workspace_id, persona_id, order_id,
    )

    service = OrderService(db)
    # Validate order belongs to this workspace/persona first
    order = await service.get_order_with_items(order_id, workspace_id, persona_id)
    if not order:
        logger.warning(
            "orders.items.not_found user_id=%s order_id=%s",
            user_id, order_id,
        )
        raise NotFoundError("Order not found")

    items = order.get("items", [])
    logger.info(
        "orders.items.response user_id=%s order_id=%s items=%s",
        user_id, order_id, len(items),
    )
    return {"success": True, "message": "Order items retrieved successfully", "data": items}


# ---------------------------------------------------------------------------
# POST /orders/{order_id}/transaction
# ---------------------------------------------------------------------------

@router.post("/{order_id}/transaction", response_model=BaseResponse, status_code=201)
async def create_transaction(
    order_id: str,
    request: CreateTransactionRequest,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Create a payment transaction for an order."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "orders.transaction.create.request user_id=%s workspace_id=%s "
        "persona_id=%s order_id=%s payment_status=%s paid_amount=%s",
        user_id, workspace_id, persona_id, order_id,
        request.payment_status, request.paid_amount,
    )

    # Validate order exists and belongs to this workspace/persona
    order = await OrderService(db).get_order_with_items(order_id, workspace_id, persona_id)
    if not order:
        logger.warning(
            "orders.transaction.create.order_not_found user_id=%s order_id=%s",
            user_id, order_id,
        )
        raise NotFoundError("Order not found")

    data = request.model_dump()
    data["workspace_id"] = workspace_id
    data["order_id"] = order_id
    data["persona_id"] = persona_id

    transaction = await OrderTransactionService(db).create_transaction(data)

    logger.info(
        "orders.transaction.create.response user_id=%s order_id=%s "
        "transaction_id=%s payment_status=%s",
        user_id, order_id, transaction.get("id"), transaction.get("payment_status"),
    )
    return {"success": True, "message": "Transaction created successfully", "data": transaction}


# ---------------------------------------------------------------------------
# GET /orders/{order_id}/transaction
# ---------------------------------------------------------------------------

@router.get("/{order_id}/transaction", response_model=BaseResponse)
async def get_order_transaction(
    order_id: str,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get the payment transaction for an order."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "orders.transaction.get.request user_id=%s workspace_id=%s "
        "persona_id=%s order_id=%s",
        user_id, workspace_id, persona_id, order_id,
    )

    # Validate order belongs to this workspace/persona
    order = await OrderService(db).get_order_with_items(order_id, workspace_id, persona_id)
    if not order:
        logger.warning(
            "orders.transaction.get.order_not_found user_id=%s order_id=%s",
            user_id, order_id,
        )
        raise NotFoundError("Order not found")

    transaction = await OrderTransactionService(db).get_transaction_by_order(order_id)
    if not transaction:
        logger.warning(
            "orders.transaction.get.not_found user_id=%s order_id=%s",
            user_id, order_id,
        )
        raise NotFoundError("Transaction not found for this order")

    logger.info(
        "orders.transaction.get.response user_id=%s order_id=%s "
        "transaction_id=%s status=%s",
        user_id, order_id, transaction.get("id"), transaction.get("payment_status"),
    )
    return {"success": True, "message": "Transaction retrieved successfully", "data": transaction}
