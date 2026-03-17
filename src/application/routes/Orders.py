from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.schemas.Order import OrderCreate, OrderUpdate, OrderResponse
from src.application.services.Order import OrderService
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationRoleCheck
from src.repositories.OrganizationRepository import OrganizationRepository
from src.repositories.TableRepository import TableRepository
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

router = APIRouter(prefix="/orders", tags=["Application Orders"])

# Public order schema
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

@router.post("", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_manager)])
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
    page: int = 1,
    page_size: int = 10,
    order_by: str = "created_at",
    order_direction: str = "desc",
    status: str = None,
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """
    Get all orders with pagination (Admin, Manager, Operator)
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    - status: Filter by order status (optional)
    """
    service = OrderService()
    
    # Validate page_size
    if page_size > 100:
        page_size = 100
    
    # Filter based on user role and access
    filters = {}
    
    user_role = user.get('role', {}).get('name')
    
    if user_role == 'Manager':
        # Manager can only see orders from their organization
        filters['organization_id'] = user.get('organization_id')
    elif user_role == 'Operator':
        # Operator can only see orders from their organization
        filters['organization_id'] = user.get('organization_id')
    
    # Add status filter if provided
    if status:
        filters['status'] = status
    
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
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }

@router.get("/{order_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_order(order_id: str, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)):
    """Get order details (Admin, Manager, Operator)"""
    service = OrderService()
    
    order = service.get_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check access based on role
    user_role = user.get('role', {}).get('name')
    
    if user_role in ['Manager', 'Operator']:
        if order.get('organization_id') != user.get('organization_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this order"
            )
    
    return {
        "success": True,
        "message": "Order retrieved successfully",
        "data": order
    }

@router.put("/{order_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_manager)])
async def update_order(order_id: str, order: OrderUpdate, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_manager)):
    """Update order (Admin, Manager)"""
    service = OrderService()
    
    # Check if order exists and user has access
    existing_order = service.get_by_id(order_id)
    
    if not existing_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    user_role = user.get('role', {}).get('name')
    
    if user_role == 'Manager':
        if existing_order.get('organization_id') != user.get('organization_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this order"
            )
    
    success = service.update(order_id, order.model_dump(exclude_unset=True))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return {
        "success": True,
        "message": "Order updated successfully"
    }

@router.delete("/{order_id}", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def delete_order(order_id: str):
    """Soft delete order (Admin only) - Data is preserved"""
    service = OrderService()
    
    success = service.soft_delete(order_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return {
        "success": True,
        "message": "Order soft deleted successfully (data preserved)"
    }

@router.put("/{order_id}/restore", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_admin)])
async def restore_order(order_id: str):
    """Restore a soft-deleted order (Admin only)"""
    service = OrderService()
    
    # Check if order exists (including deleted)
    order = service.get_by_id(order_id, include_deleted=True)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if not order.get('is_deleted', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is not deleted"
        )
    
    success = service.restore(order_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return {
        "success": True,
        "message": "Order restored successfully"
    }

@router.put("/{order_id}/status", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def update_order_status(
    order_id: str,
    status: str = Query(..., description="New status (pending, confirmed, preparing, ready, served, completed, cancelled)"),
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """Update order status (Admin, Manager, Operator)"""
    service = OrderService()
    
    # Validate status
    valid_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'served', 'completed', 'cancelled']
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Check if order exists and user has access
    existing_order = service.get_by_id(order_id)
    
    if not existing_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    user_role = user.get('role', {}).get('name')
    
    if user_role in ['Manager', 'Operator']:
        if existing_order.get('organization_id') != user.get('organization_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this order"
            )
    
    success = service.update(order_id, {"status": status})
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return {
        "success": True,
        "message": f"Order status updated to {status}"
    }

@router.put("/{order_id}/cancel", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_manager)])
async def cancel_order(order_id: str, user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_manager)):
    """Cancel order (Admin, Manager)"""
    service = OrderService()
    
    # Check if order exists and user has access
    existing_order = service.get_by_id(order_id)
    
    if not existing_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    user_role = user.get('role', {}).get('name')
    
    if user_role == 'Manager':
        if existing_order.get('organization_id') != user.get('organization_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this order"
            )
    
    # Check if order can be cancelled
    if existing_order.get('status') in ['completed', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status: {existing_order.get('status')}"
        )
    
    success = service.update(order_id, {"status": "cancelled"})
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return {
        "success": True,
        "message": "Order cancelled successfully"
    }

@router.get("/statistics", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_order_statistics(
    workspace_id: str = Query(..., description="Workspace ID"),
    organization_id: Optional[str] = Query(None, description="Organization ID"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """Get order statistics (Admin, Manager, Operator)"""
    service = OrderService()
    
    # Build filters based on user role
    filters = {"workspace_id": workspace_id}
    user_role = user.get('role', {}).get('name')
    
    if user_role in ['Manager', 'Operator']:
        filters['organization_id'] = user.get('organization_id')
    elif organization_id:
        filters['organization_id'] = organization_id
    
    # Add date filters
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

@router.post("/bulk-update-status", response_model=BaseResponse, dependencies=[Depends(ApplicationRoleCheck.require_manager)])
async def bulk_update_order_status(
    order_ids: List[str],
    status: str,
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_manager)
):
    """Bulk update order status (Admin, Manager)"""
    service = OrderService()
    
    # Validate status
    valid_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'served', 'completed', 'cancelled']
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    updated_count = 0
    failed_orders = []
    
    for order_id in order_ids:
        try:
            # Check if order exists and user has access
            existing_order = service.get_by_id(order_id)
            
            if not existing_order:
                failed_orders.append({"id": order_id, "reason": "Order not found"})
                continue
            
            user_role = user.get('role', {}).get('name')
            
            if user_role == 'Manager':
                if existing_order.get('organization_id') != user.get('organization_id'):
                    failed_orders.append({"id": order_id, "reason": "Access denied"})
                    continue
            
            success = service.update(order_id, {"status": status})
            if success:
                updated_count += 1
            else:
                failed_orders.append({"id": order_id, "reason": "Update failed"})
        except Exception as e:
            failed_orders.append({"id": order_id, "reason": str(e)})
    
    return {
        "success": True,
        "message": f"Updated {updated_count} orders to status: {status}",
        "data": {
            "updated_count": updated_count,
            "failed_orders": failed_orders
        }
    }

# ==================== PUBLIC ORDER ENDPOINTS ====================

@router.post("/public/{organization_id}/{table_id}/create")
async def create_public_order(
    organization_id: str,
    table_id: str,
    order: PublicOrderCreate
):
    """
    Create order from public menu
    Public endpoint - no authentication required
    """
    org_repo = OrganizationRepository()
    table_repo = TableRepository()
    service = OrderService()
    
    # Validate organization
    organization = org_repo.get_by_id(organization_id)
    if not organization or not organization.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive"
        )
    
    # Validate table
    table = table_repo.get_by_id(table_id)
    if not table or not table.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive"
        )
    
    # Verify table belongs to organization
    if table.get('workspace_id') != organization.get('workspace_id'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Table does not belong to this organization"
        )
    
    # Calculate totals
    subtotal = sum(item.total_price for item in order.items)
    tax_amount = subtotal * 0.05  # 5% tax (adjust as needed)
    service_charge = subtotal * 0.10  # 10% service charge (adjust as needed)
    total_amount = subtotal + tax_amount + service_charge
    
    # Prepare order data
    order_data = {
        "organization_id": organization_id,
        "workspace_id": organization.get('workspace_id'),
        "table_id": table_id,
        "area_id": table.get('area_id'),
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "items": [item.model_dump() for item in order.items],
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "service_charge": service_charge,
        "total_amount": total_amount,
        "currency": "INR",
        "order_type": 0,  # Online order
        "status": "pending",
        "payment_status": "unpaid",
        "special_instructions": order.special_instructions
    }
    
    # Create order
    order_id = service.create_order(order_data)
    
    # Get created order
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
    customer_phone: str
):
    """
    Get orders for a customer at a specific table
    Public endpoint - no authentication required
    """
    org_repo = OrganizationRepository()
    table_repo = TableRepository()
    service = OrderService()
    
    # Validate organization
    organization = org_repo.get_by_id(organization_id)
    if not organization or not organization.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive"
        )
    
    # Validate table
    table = table_repo.get_by_id(table_id)
    if not table or not table.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found or inactive"
        )
    
    # Get orders for this customer at this table
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
        "data": orders
    }