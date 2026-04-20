from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.schemas.Order import OrderCreate, OrderUpdate, OrderResponse
from src.application.services.Order import OrderService
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.repositories.PersonaRepository import PersonaRepository
from src.repositories.TableRepository import TableRepository
from src.repositories.ItemRepository import ItemRepository
from src.repositories.OrderRepository import OrderRepository
from src.repositories.CustomerRepository import CustomerRepository
from src.config.Database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

router = APIRouter(prefix="/orders", tags=["Application Orders"])


# ==================== RESPONSE SERIALIZER ====================
# Returns only the fields the UI actually uses — nothing more.

def _serialize_order(order: Dict[str, Any], table_cache: Dict[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Return only the fields the UI needs.

    List view:  id, order_number, status, customer_name, table_number, total, created_at
    Drawer:     + subtotal, tax_amount, discount_amount, items_count
    """
    table_id = order.get('table_id')
    table = table_cache.get(table_id) if table_id else None
    table_number = (
        table.get('table_number') or table.get('name')
        if table else None
    )

    items: list = order.get('items') or []

    return {
        "id":              order.get('id'),
        "order_number":    order.get('order_number'),
        "status":          order.get('status', 'pending'),
        "customer_name":   order.get('customer_name'),
        "table_number":    table_number,
        "subtotal":        round(float(order.get('subtotal') or 0), 2),
        "tax_amount":      round(float(order.get('tax_amount') or 0), 2),
        "discount_amount": round(float(order.get('discount_amount') or 0), 2),
        "total":           round(float(order.get('total_amount') or order.get('total') or 0), 2),
        "items_count":     len(items),
        "created_at":      order.get('created_at') or order.get('order_date'),
    }


def _serialize_orders(orders: List[Dict[str, Any]], table_cache: Dict[Any, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_serialize_order(o, table_cache) for o in orders]


def _serialize_order_detail(order: Dict[str, Any], table_cache: Dict[Any, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Full order detail for the drawer/panel view.
    Includes items, cost breakdown, customer info.
    """
    table_id = order.get('table_id')
    table = table_cache.get(table_id) if table_id else None
    table_number = (
        table.get('table_number') or table.get('name')
        if table else None
    )

    items: list = order.get('items') or []

    return {
        "id":                   order.get('id'),
        "order_number":         order.get('order_number'),
        "status":               order.get('status', 'pending'),
        "customer_name":        order.get('customer_name'),
        "customer_phone":       order.get('customer_phone'),
        "table_number":         table_number,
        "special_instructions": order.get('special_instructions'),
        "items":                items,
        "subtotal":             round(float(order.get('subtotal') or 0), 2),
        "tax_amount":           round(float(order.get('tax_amount') or 0), 2),
        "service_charge":       round(float(order.get('service_charge') or 0), 2),
        "discount_amount":      round(float(order.get('discount_amount') or 0), 2),
        "total":                round(float(order.get('total_amount') or order.get('total') or 0), 2),
        "items_count":          len(items),
        "payment_status":       order.get('payment_status', 'unpaid'),
        "created_at":           order.get('created_at') or order.get('order_date'),
    }


# ==================== REQUEST MODELS ====================

class PublicOrderItem(BaseModel):
    """Public order item schema"""
    item_id: int
    item_name: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    total_price: float = Field(..., gt=0)


class PublicOrderCreate(BaseModel):
    """Public order creation schema"""
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_phone: str = Field(..., min_length=10, max_length=20)
    items: List[PublicOrderItem]
    special_instructions: Optional[str] = None


class BulkUpdateOrderStatusRequest(BaseModel):
    order_ids: List[int]
    new_status: str


# ==================== HELPERS ====================

def _build_scoped_filters(user: Dict[str, Any], persona_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Build filters that always scope results to the caller's workspace.
    persona_id may further narrow within that workspace.
    SuperAdmin (system user) is unrestricted but must still pass explicit filters.
    """
    filters: Dict[str, Any] = {}

    user_type = user.get('user_type', 'application')

    if user_type != 'system':
        # All application users are strictly scoped to their own workspace
        caller_workspace_id = user.get('workspace_id')
        if not caller_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to a workspace"
            )
        filters['workspace_id'] = caller_workspace_id

        # persona_id from the user's token takes precedence for
        # Manager/Operator roles; Owner/Admin may pass it as a query param
        user_role = user.get('role', {}).get('name', '')
        if user_role in ('Manager', 'Operator'):
            # Scoped to their own persona only
            filters['persona_id'] = user.get('persona_id')
        elif persona_id:
            filters['persona_id'] = persona_id

    return filters


def _assert_order_workspace(user: Dict[str, Any], order: Dict[str, Any]) -> None:
    """
    Raise 404 if a non-SuperAdmin caller tries to access an order outside
    their workspace (or persona for Manager/Operator).
    """
    if user.get('user_type', 'application') == 'system':
        return

    caller_workspace_id = user.get('workspace_id')
    if order.get('workspace_id') != caller_workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    user_role = user.get('role', {}).get('name', '')
    if user_role in ('Manager', 'Operator'):
        if order.get('persona_id') != user.get('persona_id'):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")


# ==================== PUBLIC ORDER ENDPOINTS (must be BEFORE /{order_id}) ====================

@router.post("/public/{persona_id}/{table_id}/create")
async def create_public_order(
    persona_id: int,
    table_id: int,
    order: PublicOrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create order from public menu.
    Public endpoint - no authentication required.

    Automatically creates or updates the Customer record identified by
    (mobile, workspace_id) before persisting the order.
    """
    persona_repo = PersonaRepository(db)
    table_repo = TableRepository(db)
    service = OrderService(db)

    persona = await persona_repo.get_by_id(persona_id)
    if not persona or not persona.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found or inactive"
        )

    table = await table_repo.get_by_id(table_id)
    if not table or not table.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive"
        )

    item_repo = ItemRepository(db)
    validated_items = []

    for order_item in order.items:
        db_item = await item_repo.get_by_id(order_item.item_id)
        if not db_item or not db_item.get('is_active', False):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item '{order_item.item_id}' not found or unavailable"
            )

        server_unit_price = float(db_item.get('price', 0))
        expected_total = round(server_unit_price * order_item.quantity, 2)
        submitted_total = round(order_item.total_price, 2)

        if abs(submitted_total - expected_total) > 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Price mismatch for item '{db_item.get('name', order_item.item_id)}': "
                    f"expected total {expected_total} "
                    f"(unit price {server_unit_price} x qty {order_item.quantity}), "
                    f"got {submitted_total}"
                )
            )

        validated_items.append({
            "item_id": order_item.item_id,
            "item_name": db_item.get('name', order_item.item_name),
            "quantity": order_item.quantity,
            "unit_price": server_unit_price,
            "total_price": expected_total,
        })

    subtotal = sum(item['total_price'] for item in validated_items)
    tax_amount = subtotal * 0.05
    service_charge = subtotal * 0.10
    total_amount = subtotal + tax_amount + service_charge

    # ------------------------------------------------------------------ #
    # Customer lookup / upsert                                            #
    # ------------------------------------------------------------------ #
    workspace_id: int = int(persona.get('workspace_id'))
    customer_repo = CustomerRepository(db)

    existing_customer = await customer_repo.get_by_mobile_and_workspace(
        mobile=order.customer_phone,
        workspace_id=workspace_id,
    )

    if existing_customer:
        customer_id: int = int(existing_customer['id'])
        # Update name if the customer provided a different one this visit
        if existing_customer.get('name') != order.customer_name:
            await customer_repo.update(customer_id, {"name": order.customer_name})
    else:
        new_customer = await customer_repo.create({
            "name": order.customer_name,
            "mobile": order.customer_phone,
            "workspace_id": workspace_id,
        })
        customer_id = int(new_customer['id'])

    # ------------------------------------------------------------------ #
    # Build and persist the order                                         #
    # ------------------------------------------------------------------ #
    order_data = {
        "persona_id": persona_id,
        "workspace_id": workspace_id,
        "table_id": table_id,
        "area_id": table.get('area_id'),
        "customer_id": customer_id,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "items": validated_items,
        "subtotal": round(subtotal, 2),
        "tax_amount": round(tax_amount, 2),
        "service_charge": round(service_charge, 2),
        "total_amount": round(total_amount, 2),
        "currency": "INR",
        "order_type": 0,
        "status": "pending",
        "payment_status": "unpaid",
        "special_instructions": order.special_instructions
    }

    order_id = await service.create_order(order_data)
    created_order = await service.get_by_id(order_id)

    return {
        "success": True,
        "message": "Order created successfully",
        "data": {
            "order_id": order_id,
            "order_number": created_order.get('order_number'),
            "total_amount": total_amount,
            "status": "pending",
            "customer_id": customer_id,
        }
    }


@router.get("/public/{persona_id}/{table_id}/orders")
async def get_public_orders(
    persona_id: int,
    table_id: int,
    customer_phone: Optional[str] = Query(None, description="Customer phone number (backward compat)"),
    customer_id: Optional[int] = Query(None, description="Customer ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get orders for a customer at a specific table.
    Public endpoint - no authentication required.

    Accepts either customer_phone (backward compat) or customer_id.
    At least one must be provided.
    """
    if not customer_phone and not customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either customer_phone or customer_id must be provided"
        )

    persona_repo = PersonaRepository(db)
    table_repo = TableRepository(db)

    persona = await persona_repo.get_by_id(persona_id)
    if not persona or not persona.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found or inactive"
        )

    table = await table_repo.get_by_id(table_id)
    if not table or not table.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive"
        )

    order_repo = OrderRepository(db)

    # Build filters — prefer customer_id when both are supplied
    order_filters: Dict[str, Any] = {
        "persona_id": persona_id,
        "table_id": table_id,
        "is_active": True,
    }

    if customer_id:
        order_filters["customer_id"] = customer_id
    elif customer_phone:
        order_filters["customer_phone"] = customer_phone

    orders = await order_repo.get_all(
        filters=order_filters,
        order_by="created_at",
        order_direction="desc"
    )

    # Build per-request table cache for serialization
    table_cache: Dict[Any, Dict[str, Any]] = {table_id: table}

    return {
        "success": True,
        "message": "Orders retrieved successfully",
        "data": _serialize_orders(orders, table_cache)
    }


# ==================== COLLECTION ENDPOINTS ====================

@router.post("", response_model=BaseResponse)
async def create_order(
    order: OrderCreate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('orders:create')),
    db: AsyncSession = Depends(get_db)
):
    """Create new order (Admin, Manager)"""
    service = OrderService(db)

    order_id = await service.create_order(order.model_dump())

    return {
        "success": True,
        "message": "Order created successfully",
        "data": {"id": order_id}
    }


@router.get("")
async def get_all_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    order_by: str = Query("created_at"),
    order_direction: str = Query("desc"),
    workspace_id: Optional[int] = Query(None, description="SuperAdmin only"),
    persona_id: Optional[int] = Query(None, description="Filter by persona"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('orders:read')),
    db: AsyncSession = Depends(get_db)
):
    """
    Get orders with pagination, always scoped to the caller's workspace
    and optionally narrowed by persona and date range.

    - Owner/Admin: scoped to workspace, may filter by persona_id
    - Manager/Operator: scoped to their own persona within their workspace
    - SuperAdmin: unrestricted, may pass workspace_id / persona_id as query params
    """
    service = OrderService(db)

    if page_size > 100:
        page_size = 100

    filters = _build_scoped_filters(user, persona_id=persona_id)

    # SuperAdmin explicit filters
    if user.get('user_type') == 'system':
        if workspace_id:
            filters['workspace_id'] = workspace_id
        if persona_id:
            filters['persona_id'] = persona_id

    if status:
        filters['status'] = status

    items, total, total_pages = await service.get_paginated_orders(
        workspace_id=filters.get('workspace_id'),
        page=page,
        page_size=page_size,
        filters=filters,
        order_by=order_by,
        order_direction=order_direction,
        include_deleted=False,
        start_date=start_date,
        end_date=end_date
    )

    # Build per-request table cache for serialization
    table_cache: Dict[Any, Dict[str, Any]] = {}
    table_repo = TableRepository(db)
    for order in items:
        tid = order.get('table_id')
        if tid and tid not in table_cache:
            table_cache[tid] = await table_repo.get_by_id(tid) or {}

    return {
        "success": True,
        "message": "Orders retrieved successfully",
        "data": _serialize_orders(items, table_cache),
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


# ==================== STATIC-PATH ENDPOINTS (must be BEFORE /{order_id}) ====================

@router.get("/statistics", response_model=BaseResponse)
async def get_order_statistics(
    persona_id: Optional[int] = Query(None, description="Filter by persona"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('orders:read')),
    db: AsyncSession = Depends(get_db)
):
    """Get order statistics scoped to the caller's workspace (Admin, Manager, Operator)"""
    service = OrderService(db)

    filters = _build_scoped_filters(user, persona_id=persona_id)

    stats = await service.get_statistics(
        workspace_id=filters.get('workspace_id'),
        persona_id=filters.get('persona_id'),
        start_date=start_date,
        end_date=end_date
    )

    return {
        "success": True,
        "message": "Order statistics retrieved successfully",
        "data": stats
    }


@router.post("/bulk-update-status", response_model=BaseResponse)
async def bulk_update_order_status(
    body: BulkUpdateOrderStatusRequest,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('orders:update')),
    db: AsyncSession = Depends(get_db)
):
    """Bulk update order status (Admin, Manager) — only within the caller's scope"""
    service = OrderService(db)

    valid_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'served', 'completed', 'cancelled']
    if body.new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    updated_count = 0
    failed_orders = []

    for order_id in body.order_ids:
        try:
            existing_order = await service.get_by_id(order_id)

            if not existing_order:
                failed_orders.append({"id": order_id, "reason": "Order not found"})
                continue

            # Enforce workspace / persona scope
            try:
                _assert_order_workspace(user, existing_order)
            except HTTPException:
                failed_orders.append({"id": order_id, "reason": "Access denied"})
                continue

            success = await service.update(order_id, {"status": body.new_status})
            if success:
                updated_count += 1
            else:
                failed_orders.append({"id": order_id, "reason": "Update failed"})
        except Exception as e:
            failed_orders.append({"id": order_id, "reason": str(e)})

    return {
        "success": True,
        "message": f"Updated {updated_count} orders to status: {body.new_status}",
        "data": {
            "updated_count": updated_count,
            "failed_orders": failed_orders
        }
    }


# ==================== ORDER-SCOPED ENDPOINTS (/{order_id}) ====================

@router.get("/{order_id}", response_model=BaseResponse)
async def get_order(
    order_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('orders:read')),
    db: AsyncSession = Depends(get_db)
):
    """Get order details (Admin, Manager, Operator)"""
    service = OrderService(db)

    order = await service.get_by_id(order_id)

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _assert_order_workspace(user, order)

    # Build per-request table cache for serialization
    table_cache: Dict[Any, Dict[str, Any]] = {}
    tid = order.get('table_id')
    if tid:
        table_repo = TableRepository(db)
        table_cache[tid] = await table_repo.get_by_id(tid) or {}

    return {
        "success": True,
        "message": "Order retrieved successfully",
        "data": _serialize_order_detail(order, table_cache)
    }


@router.put("/{order_id}", response_model=BaseResponse)
async def update_order(
    order_id: int,
    order: OrderUpdate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('orders:update')),
    db: AsyncSession = Depends(get_db)
):
    """Update order (Admin, Manager)"""
    service = OrderService(db)

    existing_order = await service.get_by_id(order_id)

    if not existing_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _assert_order_workspace(user, existing_order)

    success = await service.update(order_id, order.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {
        "success": True,
        "message": "Order updated successfully"
    }


@router.delete("/{order_id}", response_model=BaseResponse)
async def delete_order(
    order_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('orders:delete')),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete order (Admin only) - Data is preserved"""
    service = OrderService(db)

    existing_order = await service.get_by_id(order_id)
    if not existing_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _assert_order_workspace(user, existing_order)

    success = await service.soft_delete(order_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {
        "success": True,
        "message": "Order soft deleted successfully (data preserved)"
    }


@router.put("/{order_id}/restore", response_model=BaseResponse)
async def restore_order(
    order_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('orders:restore')),
    db: AsyncSession = Depends(get_db)
):
    """Restore a soft-deleted order (Admin only)"""
    service = OrderService(db)

    order = await service.get_by_id(order_id, include_deleted=True)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _assert_order_workspace(user, order)

    # is_active=True means active (not deleted); raise error if not deleted
    if order.get('is_active', True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is not deleted")

    success = await service.restore(order_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {
        "success": True,
        "message": "Order restored successfully"
    }


@router.put("/{order_id}/status", response_model=BaseResponse)
async def update_order_status(
    order_id: int,
    new_status: str = Query(..., description="New status (pending, confirmed, preparing, ready, served, completed, cancelled)"),
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('orders:update')),
    db: AsyncSession = Depends(get_db)
):
    """Update order status (Admin, Manager, Operator)"""
    service = OrderService(db)

    valid_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'served', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    existing_order = await service.get_by_id(order_id)

    if not existing_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _assert_order_workspace(user, existing_order)

    success = await service.update(order_id, {"status": new_status})

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {
        "success": True,
        "message": f"Order status updated to {new_status}"
    }


@router.put("/{order_id}/cancel", response_model=BaseResponse)
async def cancel_order(
    order_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('orders:update')),
    db: AsyncSession = Depends(get_db)
):
    """Cancel order (Admin, Manager)"""
    service = OrderService(db)

    existing_order = await service.get_by_id(order_id)

    if not existing_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _assert_order_workspace(user, existing_order)

    if existing_order.get('status') in ['completed', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status: {existing_order.get('status')}"
        )

    success = await service.update(order_id, {"status": "cancelled"})

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {
        "success": True,
        "message": "Order cancelled successfully"
    }
