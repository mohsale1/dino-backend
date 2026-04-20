from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.repositories.CustomerRepository import CustomerRepository

router = APIRouter(prefix="/customers", tags=["Customers"])


# ==================== REQUEST MODELS ====================

class CustomerUpdate(BaseModel):
    """Only the customer's name may be changed — mobile is immutable."""
    name: str = Field(..., min_length=1, max_length=200)


# ==================== HELPERS ====================

def _resolve_workspace_id(user: Dict[str, Any], requested_workspace_id: Optional[int]) -> int:
    """
    Return the effective workspace_id for the caller.

    - SuperAdmin (system): must supply workspace_id explicitly.
    - Application users: always scoped to their own workspace; the
      requested_workspace_id query param is intentionally ignored to
      prevent cross-workspace data leakage.
    """
    user_type = user.get('user_type', 'application')

    if user_type == 'system':
        if not requested_workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="workspace_id is required for SuperAdmin"
            )
        return int(requested_workspace_id)

    caller_workspace_id = user.get('workspace_id')
    if not caller_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to a workspace"
        )
    return int(caller_workspace_id)


def _assert_customer_workspace(user: Dict[str, Any], customer: Dict[str, Any]) -> None:
    """
    Raise 404 if a non-SuperAdmin caller tries to access a customer that
    does not belong to their workspace.  Using 404 avoids leaking existence.
    """
    if user.get('user_type', 'application') == 'system':
        return
    caller_workspace_id = user.get('workspace_id')
    if customer.get('workspace_id') != caller_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )


# ==================== ENDPOINTS ====================

@router.get("", response_model=BaseResponse)
async def list_customers(
    workspace_id: Optional[int] = Query(None, description="SuperAdmin only — filter by workspace"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or mobile"),
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('customers:read')),
    db: AsyncSession = Depends(get_db)
):
    """
    List all customers in the caller's workspace with pagination.

    - Application users: always scoped to their own workspace.
    - SuperAdmin: must supply workspace_id explicitly.
    """
    if page_size > 100:
        page_size = 100

    scoped_workspace_id = _resolve_workspace_id(user, workspace_id)
    repo = CustomerRepository(db)

    filters: Dict[str, Any] = {"workspace_id": scoped_workspace_id}

    # search is applied as a post-filter when the base repo does not support
    # ILIKE — keep it simple and let get_paginated handle exact-match filters,
    # then narrow by search in Python for small result sets.
    # For production scale, push search into a custom repo query.
    items, total, total_pages = await repo.get_paginated(
        page=page,
        page_size=page_size,
        filters=filters,
        order_by="created_at",
        order_direction="desc",
    )

    if search:
        search_lower = search.lower()
        items = [
            c for c in items
            if search_lower in (c.get('name') or '').lower()
            or search_lower in (c.get('mobile') or '').lower()
        ]

    return {
        "success": True,
        "message": "Customers retrieved successfully",
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


@router.get("/{customer_id}/orders", response_model=BaseResponse)
async def get_customer_order_history(
    customer_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('customers:read')),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the full order history for a customer.
    Scoped to the caller's workspace.
    """
    repo = CustomerRepository(db)

    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    _assert_customer_workspace(user, customer)

    orders = await repo.get_order_history(customer_id)

    return {
        "success": True,
        "message": "Customer order history retrieved successfully",
        "data": orders,
    }


@router.get("/{customer_id}", response_model=BaseResponse)
async def get_customer(
    customer_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('customers:read')),
    db: AsyncSession = Depends(get_db)
):
    """Get a single customer by ID, scoped to the caller's workspace."""
    repo = CustomerRepository(db)

    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    _assert_customer_workspace(user, customer)

    return {
        "success": True,
        "message": "Customer retrieved successfully",
        "data": customer,
    }


@router.put("/{customer_id}", response_model=BaseResponse)
async def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('customers:update')),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a customer's name.
    Mobile number cannot be changed — it is the customer's unique identifier.
    """
    repo = CustomerRepository(db)

    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    _assert_customer_workspace(user, customer)

    success = await repo.update(customer_id, {"name": body.name})
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return {
        "success": True,
        "message": "Customer updated successfully",
    }


@router.delete("/{customer_id}", response_model=BaseResponse)
async def delete_customer(
    customer_id: int,
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('customers:delete')),
    db: AsyncSession = Depends(get_db)
):
    """
    Soft-delete a customer (sets is_active=False).
    Data is preserved; the customer will no longer appear in active listings.
    """
    repo = CustomerRepository(db)

    customer = await repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    _assert_customer_workspace(user, customer)

    success = await repo.soft_delete(customer_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return {
        "success": True,
        "message": "Customer deleted successfully (data preserved)",
    }
