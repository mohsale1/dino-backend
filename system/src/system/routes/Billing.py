from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.schemas.Workspace import WorkspaceBillingUpdate
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.Billing import BillingService

router = APIRouter(prefix="/billing", tags=["System Billing"])


# ---------------------------------------------------------------------------
# Inline schemas for billing transactions
# ---------------------------------------------------------------------------

class BillingTransactionCreate(BaseModel):
    """Schema for creating a billing transaction."""
    workspace_id: int
    plan: str = Field(..., max_length=50)
    amount: Decimal = Field(..., ge=0)
    currency: str = Field("INR", max_length=10)
    billing_period_start: datetime
    billing_period_end: datetime
    payment_status: str = Field("pending", max_length=30)
    payment_method: Optional[str] = Field(None, max_length=50)
    payment_ref: Optional[str] = Field(None, max_length=200)
    invoice_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class BillingTransactionUpdate(BaseModel):
    """Schema for updating a billing transaction."""
    payment_status: Optional[str] = Field(None, max_length=30)
    paid_amount: Optional[Decimal] = Field(None, ge=0)
    last_paid_at: Optional[datetime] = None
    payment_ref: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/workspaces",
    dependencies=[Depends(SystemPermissionCheck.require("billing:read"))],
)
async def get_all_billing(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated workspace billing records."""
    service = BillingService(db)
    items, total, total_pages = await service.get_all_billing(page=page, page_size=page_size)
    return {
        "success": True,
        "message": "Billing records retrieved successfully",
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


@router.get(
    "/workspaces/{workspace_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("billing:read"))],
)
async def get_workspace_billing(workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Get billing information for a specific workspace."""
    service = BillingService(db)
    billing = await service.get_workspace_billing(workspace_id)
    if not billing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found",
        )
    return {"success": True, "message": "Billing retrieved successfully", "data": billing}


@router.put(
    "/workspaces/{workspace_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("billing:update"))],
)
async def update_workspace_billing(
    workspace_id: int,
    billing_data: WorkspaceBillingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update billing information for a workspace."""
    service = BillingService(db)
    success = await service.update_billing_info(
        workspace_id, billing_data.model_dump(exclude_unset=True)
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found",
        )
    return {"success": True, "message": "Billing updated successfully"}


@router.get(
    "/stats",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("billing:read"))],
)
async def get_billing_stats(db: AsyncSession = Depends(get_db)):
    """Get aggregate billing statistics."""
    service = BillingService(db)
    stats = await service.get_billing_stats()
    return {"success": True, "message": "Billing stats retrieved successfully", "data": stats}


@router.get(
    "/transactions",
    dependencies=[Depends(SystemPermissionCheck.require("billing:read"))],
)
async def get_billing_transactions(
    workspace_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated billing transactions."""
    service = BillingService(db)
    items, total, total_pages = await service.get_billing_transactions(
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
    )
    return {
        "success": True,
        "message": "Billing transactions retrieved successfully",
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


@router.post(
    "/transactions",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("billing:subscription"))],
)
async def create_billing_transaction(
    transaction_data: BillingTransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a billing transaction record."""
    service = BillingService(db)
    created = await service.create_billing_transaction(transaction_data.model_dump())
    return {
        "success": True,
        "message": "Billing transaction created successfully",
        "data": {"id": created.get("id")},
    }


@router.put(
    "/transactions/{transaction_id}",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("billing:update"))],
)
async def update_billing_transaction(
    transaction_id: int,
    update_data: BillingTransactionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a billing transaction."""
    service = BillingService(db)
    success = await service.update_billing_transaction(
        transaction_id, update_data.model_dump(exclude_unset=True)
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing transaction not found",
        )
    return {"success": True, "message": "Billing transaction updated successfully"}
