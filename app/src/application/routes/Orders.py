from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.schemas.Order import OrderCreate, OrderUpdate, OrderResponse
from src.application.services.Order import OrderService
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationRoleCheck
from src.repositories.OrganizationRepository import OrganizationRepository
from src.repositories.TableRepository import TableRepository
from src.repositories.ItemRepository import ItemRepository
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

router = APIRouter(prefix="/orders", tags=["Application Orders"])


# ==================== RESPONSE SERIALIZER ====================
# Returns only the fields the UI actually uses — nothing more.

# Module-level table cache to avoid repeated Firestore lookups within a request
_table_cache: Dict[str, Dict[str, Any]] = {}

def _get_table(table_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Fetch table from cache or Firestore."""
    if not table_id:
        return None
    if table_id not in _table_cache:
        table_repo = TableRepository()
        _table_cache[table_id] = table_repo.get_by_id(table_id) or {}
    return _table_cache[table_id]


def _serialize_order(order: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return only the fields the UI needs.

    List view:  id, order_number, status, customer_name, table_number, total, created_at
    Drawer:     + subtotal, tax_amount, discount_amount, items_count
    """
    table = _get_table(order.get('table_id'))
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


def _serialize_orders(orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Clear per-request cache before bulk serialization
    _table_cache.clear()
    return [_serialize_order(o) for o in orders]


def _serialize_order_detail(order: Dict[str, Any]) -> Dict[str, Any]:
    """
    Full order detail for the drawer/panel view.
    Includes items, cost breakdown, customer info.
    """
    table = _get_table(order.get('table_id'))
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
    item_id: str
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
    order_ids: List[str]
    new_status: str


# ==================== HELPERS ====================

def _build_scoped_filters(user: Dict[str, Any], organization_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Build Firestore filters that always scope results to the caller's workspace.
    organization_id may further narrow within that workspace.
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

        # organization_id from the user's token takes precedence for
        # Manager/Operator roles; Owner/Admin may pass it as a query param
        user_role = user.get('role', {}).get('name', '')
        if user_role in ('Manager', 'Operator'):
            # Scoped to their own organization only
            filters['organization_id'] = user.get('organization_id')
        elif organization_id:
            filters['organization_id'] = organization_id

    return filters


def _assert_order_workspace(user: Dict[str, Any], order: Dict[str, Any]) -> None:
    """
    Raise 404 if a non-SuperAdmin caller tries to access an order outside
    their workspace (or organization for Manager/Operator).
    """
    if user.get('user_type', 'application') == 'system':
        return

    caller_workspace_id = user.get('workspace_id')
    if order.get('workspace_id') != caller_workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    user_role = user.get('role', {}).get('name', '')
    if user_role in ('Manager', 'Operator'):
        if order.get('organization_id') != user.get('organization_id'):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")


# ==================== COLLECTION ENDPOINTS ====================

@router.post("", response_model=BaseResponse)
async def create_order(order: OrderCreate, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_manager)):
    """Create new order (Admin, Manager)"""
    service = OrderService()

    order_id = service.create_order(order.model_dump())

    return {
        "success": True,
        "message": "Order created successfully",
        "data": {"id": order_id}
    }


@router.get("", dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_all_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    order_by: str = Query("created_at"),
    order_direction: str = Query("desc"),
    workspace_id: Optional[str] = Query(None, description="SuperAdmin only"),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    status: Optional[str] = Query(None, description="Filter by order status"),
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """
    Get orders with pagination, always scoped to the caller's workspace
    and optionally narrowed by organization and date range.

    - Owner/Admin: scoped to workspace, may filter by organization_id
    - Manager/Operator: scoped to their own organization within their workspace
    - SuperAdmin: unrestricted, may pass workspace_id / organization_id as query params
    """
    from datetime import datetime, timezone

    service = OrderService()

    if page_size > 100:
        page_size = 100

    filters = _build_scoped_filters(user, organization_id=organization_id)

    # SuperAdmin explicit filters
    if user.get('user_type') == 'system':
        if workspace_id:
            filters['workspace_id'] = workspace_id
        if organization_id:
            filters['organization_id'] = organization_id

    if status:
        filters['status'] = status

    # Fetch all matching docs first (date filtering is done in-memory
    # because Firestore requires composite indexes for range + equality queries)
    if start_date or end_date:
        # Fetch all without pagination, then filter by date, then paginate in Python
        all_items = service.get_all(filters=filters if filters else None)

        def _parse_boundary(value: str, end_of_day: bool = False) -> Optional[datetime]:
            try:
                # Accept both YYYY-MM-DD and full ISO strings
                if 'T' in value:
                    dt = datetime.fromisoformat(value)
                else:
                    dt = datetime.fromisoformat(value)
                    if end_of_day:
                        dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                return None

        start_dt = _parse_boundary(start_date) if start_date else None
        end_dt = _parse_boundary(end_date, end_of_day=True) if end_date else None

        def _in_range(order: Dict[str, Any]) -> bool:
            created = order.get('created_at') or order.get('order_date')
            if created is None:
                return False
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created)
                except ValueError:
                    return False
            if not isinstance(created, datetime):
                return False
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if start_dt and created < start_dt:
                return False
            if end_dt and created > end_dt:
                return False
            return True

        filtered = [o for o in all_items if _in_range(o)]

        # Sort in Python
        reverse = order_direction.lower() == 'desc'
        filtered.sort(
            key=lambda d: (d.get(order_by) is None, d.get(order_by)),
            reverse=reverse
        )

        # Paginate in Python
        total = len(filtered)
        total_pages = max(1, (total + page_size - 1) // page_size)
        offset = (page - 1) * page_size
        items = filtered[offset: offset + page_size]

    else:
        items, total, total_pages = service.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters if filters else None,
            order_by=order_by,
            order_direction=order_direction
        )

    return {
        "success": True,
        "message": "Orders retrieved successfully",
        "data": _serialize_orders(items),
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

@router.get("/statistics", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_order_statistics(
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """Get order statistics scoped to the caller's workspace (Admin, Manager, Operator)"""
    service = OrderService()

    filters = _build_scoped_filters(user, organization_id=organization_id)

    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date

    stats = service.get_statistics(filters)

    return {
        "success": True,
        "message": "Order statistics retrieved successfully",
        "data": stats
    }


@router.post("/bulk-update-status", response_model=BaseResponse)
async def bulk_update_order_status(
    body: BulkUpdateOrderStatusRequest,
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_manager)
):
    """Bulk update order status (Admin, Manager) — only within the caller's scope"""
    service = OrderService()

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
            existing_order = service.get_by_id(order_id)

            if not existing_order:
                failed_orders.append({"id": order_id, "reason": "Order not found"})
                continue

            # Enforce workspace / organization scope
            try:
                _assert_order_workspace(user, existing_order)
            except HTTPException:
                failed_orders.append({"id": order_id, "reason": "Access denied"})
                continue

            success = service.update(order_id, {"status": body.new_status})
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

@router.get("/{order_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_order(order_id: str, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)):
    """Get order details (Admin, Manager, Operator)"""
    service = OrderService()

    order = service.get_by_id(order_id)

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _assert_order_workspace(user, order)

    return {
        "success": True,
        "message": "Order retrieved successfully",
        "data": _serialize_order_detail(order)
    }


@router.put("/{order_id}", response_model=BaseResponse)
async def update_order(order_id: str, order: OrderUpdate, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_manager)):
    """Update order (Admin, Manager)"""
    service = OrderService()

    existing_order = service.get_by_id(order_id)

    if not existing_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _assert_order_workspace(user, existing_order)

    success = service.update(order_id, order.model_dump(exclude_unset=True))

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {
        "success": True,
        "message": "Order updated successfully"
    }


@router.delete("/{order_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def delete_order(order_id: str, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin)):
    """Soft delete order (Admin only) - Data is preserved"""
    service = OrderService()

    existing_order = service.get_by_id(order_id)
    if not existing_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _assert_order_workspace(user, existing_order)

    success = service.soft_delete(order_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {
        "success": True,
        "message": "Order soft deleted successfully (data preserved)"
    }


@router.put("/{order_id}/restore", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def restore_order(order_id: str, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_admin)):
    """Restore a soft-deleted order (Admin only)"""
    service = OrderService()

    order = service.get_by_id(order_id, include_deleted=True)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _assert_order_workspace(user, order)

    if not order.get('is_deleted', False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is not deleted")

    success = service.restore(order_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {
        "success": True,
        "message": "Order restored successfully"
    }


@router.put("/{order_id}/status", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def update_order_status(
    order_id: str,
    new_status: str = Query(..., description="New status (pending, confirmed, preparing, ready, served, completed, cancelled)"),
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """Update order status (Admin, Manager, Operator)"""
    service = OrderService()

    valid_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'served', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    existing_order = service.get_by_id(order_id)

    if not existing_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _assert_order_workspace(user, existing_order)

    success = service.update(order_id, {"status": new_status})

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {
        "success": True,
        "message": f"Order status updated to {new_status}"
    }


@router.put("/{order_id}/cancel", response_model=BaseResponse)
async def cancel_order(order_id: str, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_manager)):
    """Cancel order (Admin, Manager)"""
    service = OrderService()

    existing_order = service.get_by_id(order_id)

    if not existing_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    _assert_order_workspace(user, existing_order)

    if existing_order.get('status') in ['completed', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status: {existing_order.get('status')}"
        )

    success = service.update(order_id, {"status": "cancelled"})

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {
        "success": True,
        "message": "Order cancelled successfully"
    }


# ==================== PUBLIC ORDER ENDPOINTS ====================

@router.post("/public/{organization_id}/{table_id}/create")
async def create_public_order(
    organization_id: str,
    table_id: str,
    order: PublicOrderCreate
):
    """
    Create order from public menu.
    Public endpoint - no authentication required.
    """
    org_repo = OrganizationRepository()
    table_repo = TableRepository()
    service = OrderService()

    organization = org_repo.get_by_id(organization_id)
    if not organization or not organization.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive"
        )

    table = table_repo.get_by_id(table_id)
    if not table or not table.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive"
        )

    item_repo = ItemRepository()
    validated_items = []

    for order_item in order.items:
        db_item = item_repo.get_by_id(order_item.item_id)
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

    order_data = {
        "organization_id": organization_id,
        "workspace_id": organization.get('workspace_id'),
        "table_id": table_id,
        "area_id": table.get('area_id'),
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

    order_id = service.create_order(order_data)
    created_order = service.get_by_id(order_id)

    return {
        "success": True,
        "message": "Order created successfully",
        "data": {
            "order_id": order_id,
            "order_number": created_order.get('order_number'),
            "total_amount": total_amount,
            "status": "pending"
        }
    }


@router.get("/public/{organization_id}/{table_id}/orders")
async def get_public_orders(
    organization_id: str,
    table_id: str,
    customer_phone: str = Query(..., description="Customer phone number")
):
    """
    Get orders for a customer at a specific table.
    Public endpoint - no authentication required.
    """
    org_repo = OrganizationRepository()
    table_repo = TableRepository()
    service = OrderService()

    organization = org_repo.get_by_id(organization_id)
    if not organization or not organization.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive"
        )

    table = table_repo.get_by_id(table_id)
    if not table or not table.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive"
        )

    from src.repositories.OrderRepository import OrderRepository
    order_repo = OrderRepository()

    orders = order_repo.get_all(
        filters={
            "organization_id": organization_id,
            "table_id": table_id,
            "customer_phone": customer_phone,
            "is_active": True
        },
        order_by="created_at",
        order_direction="desc"
    )

    return {
        "success": True,
        "message": "Orders retrieved successfully",
        "data": _serialize_orders(orders)
    }