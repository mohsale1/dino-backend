"""
Customers router — CRUD for customer records.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Customer import CustomerService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/customers", tags=["Customers"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateCustomerRequest(BaseModel):
    name: str
    mobile: str
    workspace_id: Optional[int] = None
    persona_id: Optional[int] = None


class UpdateCustomerRequest(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None
    persona_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_customers(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("customers:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated customers."""
    wid = workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = CustomerService(db)
    items, total, total_pages = await service.get_paginated_customers(
        workspace_id=wid,
        persona_id=persona_id,
        search=search,
        page=page,
        page_size=page_size,
    )
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


@router.post("", response_model=BaseResponse)
async def create_customer(
    request: CreateCustomerRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("customers:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create or retrieve a customer by mobile + workspace."""
    wid = request.workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="workspace_id required")
    service = CustomerService(db)
    customer = await service.create_or_get_customer(
        name=request.name,
        mobile=request.mobile,
        workspace_id=wid,
        persona_id=request.persona_id,
    )
    return {"success": True, "message": "Customer created successfully", "data": customer}


@router.get("/{customer_id}", response_model=BaseResponse)
async def get_customer(
    customer_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("customers:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a customer by ID."""
    service = CustomerService(db)
    customer = await service.get_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return {"success": True, "message": "Customer retrieved successfully", "data": customer}


@router.put("/{customer_id}", response_model=BaseResponse)
async def update_customer(
    customer_id: int,
    request: UpdateCustomerRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("customers:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a customer."""
    service = CustomerService(db)
    existing = await service.get_by_id(customer_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    data = request.model_dump(exclude_unset=True)
    success = await service.update_customer(customer_id, data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return {"success": True, "message": "Customer updated successfully"}


@router.delete("/{customer_id}", response_model=BaseResponse)
async def delete_customer(
    customer_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("customers:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a customer."""
    service = CustomerService(db)
    existing = await service.get_by_id(customer_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    success = await service.soft_delete_customer(customer_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return {"success": True, "message": "Customer deleted successfully"}


@router.get("/{customer_id}/orders", response_model=BaseResponse)
async def get_customer_orders(
    customer_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("customers:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get order history for a customer."""
    service = CustomerService(db)
    existing = await service.get_by_id(customer_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    items, total, total_pages = await service.get_customer_orders(
        customer_id=customer_id,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "message": "Customer orders retrieved successfully",
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
