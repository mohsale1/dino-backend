"""
Customers router — CRUD for customer records.
No workspace or persona scoping — mobile is globally unique.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Customer import CustomerService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError

router = APIRouter(prefix="/customers", tags=["Customers"])


class CreateCustomerRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    mobile: str = Field(..., min_length=7, max_length=30, pattern=r'^\+?[0-9\s\-\(\)]{7,30}$')


class UpdateCustomerRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    mobile: Optional[str] = Field(None, min_length=7, max_length=30, pattern=r'^\+?[0-9\s\-\(\)]{7,30}$')


@router.get("", response_model=BaseResponse)
async def get_customers(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("customers:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated customers with optional name/mobile search."""
    items, total, total_pages = await CustomerService(db).get_paginated_customers(
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
    """Create or retrieve a customer by mobile number."""
    customer = await CustomerService(db).create_or_get_customer(
        name=request.name,
        mobile=request.mobile,
    )
    return {"success": True, "message": "Customer created successfully", "data": customer}


@router.get("/{customer_id}", response_model=BaseResponse)
async def get_customer(
    customer_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("customers:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a customer by ID."""
    customer = await CustomerService(db).get_by_id(customer_id)
    if not customer:
        raise NotFoundError("Customer not found")
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
        raise NotFoundError("Customer not found")
    data = request.model_dump(exclude_unset=True)
    if not data:
        raise BadRequestError("No fields provided for update")
    success = await service.update_customer(customer_id, data)
    if not success:
        raise NotFoundError("Customer not found")
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
        raise NotFoundError("Customer not found")
    success = await service.soft_delete_customer(customer_id)
    if not success:
        raise NotFoundError("Customer not found")
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
        raise NotFoundError("Customer not found")
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
