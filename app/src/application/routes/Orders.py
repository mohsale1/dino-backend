"""
Orders router — CRUD for order_details, order line items, and transactions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Order import OrderService
from src.application.services.OrderTransaction import OrderTransactionService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/orders", tags=["Orders"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class OrderItemIn(BaseModel):
    item_id: int
    quantity: int = 1


class CreateOrderRequest(BaseModel):
    workspace_id: int
    persona_id: int
    order_type: str = "dine_in"
    customer_id: Optional[int] = None
    customer_name: str = "Guest"
    table_id: Optional[int] = None
    area_id: Optional[int] = None
    currency: str = "INR"
    special_instructions: Optional[str] = None
    tax_amount: Optional[float] = 0.0
    service_charge: Optional[float] = 0.0
    discount_amount: Optional[float] = 0.0
    items: List[OrderItemIn]


class UpdateStatusRequest(BaseModel):
    status: str


class CreateTransactionRequest(BaseModel):
    workspace_id: int
    persona_id: int
    customer_id: Optional[int] = None
    paid_amount: float = 0.0
    total_amount: float
    currency: str = "INR"
    payment_method: Optional[str] = None
    payment_status: str = "unpaid"
    payment_ref: Optional[str] = None
    notes: Optional[str] = None


class UpdateTransactionRequest(BaseModel):
    paid_amount: Optional[float] = None
    total_amount: Optional[float] = None
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None
    payment_ref: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=BaseResponse)
async def create_order(
    request: CreateOrderRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("orders:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new order with line items atomically."""
    service = OrderService(db)
    data = request.model_dump()
    data["items"] = [i.model_dump() for i in request.items]
    data["created_by"] = current_user.get("id")
    try:
        order = await service.create_order(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"success": True, "message": "Order created successfully", "data": order}


@router.get("/statistics", response_model=BaseResponse)
async def get_order_statistics(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("orders:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated order statistics."""
    wid = workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = OrderService(db)
    stats = await service.get_order_statistics(
        workspace_id=wid,
        persona_id=persona_id,
        start_date=start_date,
        end_date=end_date,
    )
    return {"success": True, "message": "Statistics retrieved", "data": stats}


@router.get("/transactions", response_model=BaseResponse)
async def get_transactions(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    payment_status: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("orders:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated order transactions."""
    wid = workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = OrderTransactionService(db)
    items, total, total_pages = await service.get_paginated_transactions(
        workspace_id=wid,
        persona_id=persona_id,
        payment_status=payment_status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
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


@router.put("/transactions/{transaction_id}", response_model=BaseResponse)
async def update_transaction(
    transaction_id: int,
    request: UpdateTransactionRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("orders:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a payment transaction."""
    service = OrderTransactionService(db)
    existing = await service.get_by_id(transaction_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    data = request.model_dump(exclude_unset=True)
    success = await service.update_transaction(transaction_id, data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return {"success": True, "message": "Transaction updated successfully"}


@router.get("", response_model=BaseResponse)
async def get_orders(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    order_status: Optional[str] = Query(None, alias="status"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("orders:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated order list."""
    wid = workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = OrderService(db)
    items, total, total_pages = await service.get_paginated_orders(
        workspace_id=wid,
        persona_id=persona_id,
        status=order_status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
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


@router.get("/{order_id}", response_model=BaseResponse)
async def get_order(
    order_id: str,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("orders:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single order with its line items."""
    service = OrderService(db)
    order = await service.get_order_with_items(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return {"success": True, "message": "Order retrieved successfully", "data": order}


@router.put("/{order_id}/status", response_model=BaseResponse)
async def update_order_status(
    order_id: str,
    request: UpdateStatusRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("orders:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update the status of an order."""
    service = OrderService(db)
    success = await service.update_order_status(order_id, request.status)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return {"success": True, "message": "Order status updated successfully"}


@router.put("/{order_id}/cancel", response_model=BaseResponse)
async def cancel_order(
    order_id: str,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("orders:update")),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an order."""
    service = OrderService(db)
    success = await service.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return {"success": True, "message": "Order cancelled successfully"}


@router.get("/{order_id}/items", response_model=BaseResponse)
async def get_order_items(
    order_id: str,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("orders:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get all line items for an order."""
    service = OrderService(db)
    items = await service.get_order_items(order_id)
    return {"success": True, "message": "Order items retrieved successfully", "data": items}


@router.post("/{order_id}/transaction", response_model=BaseResponse)
async def create_transaction(
    order_id: str,
    request: CreateTransactionRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("orders:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a payment transaction for an order."""
    # Verify order exists
    order_service = OrderService(db)
    order = await order_service.get_order_with_items(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    tx_service = OrderTransactionService(db)
    data = request.model_dump()
    data["order_id"] = order_id
    transaction = await tx_service.create_transaction(data)
    return {"success": True, "message": "Transaction created successfully", "data": transaction}


@router.get("/{order_id}/transaction", response_model=BaseResponse)
async def get_order_transaction(
    order_id: str,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("orders:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the payment transaction for an order."""
    service = OrderTransactionService(db)
    transaction = await service.get_transaction_by_order(order_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return {"success": True, "message": "Transaction retrieved successfully", "data": transaction}
