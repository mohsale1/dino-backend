"""
Billing router — workspace billing management APIs for the UI.

Endpoints
---------
GET  /billing/overview                    — full billing summary (plan + detail + tx summary)
GET  /billing/config?persona_id=X         — per-persona tax/service charge config
PUT  /billing/config?persona_id=X         — upsert billing config
GET  /billing/transactions                — paginated billing transactions
GET  /billing/due                         — paginated workspaces with billing due (admin)
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Billing import BillingService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class UpsertBillingConfigRequest(BaseModel):
    tax_rate: Optional[Decimal] = Field(None, ge=0, le=1, description="Fractional: 0.05 = 5%")
    tax_label: Optional[str] = Field(None, max_length=100)
    service_charge_rate: Optional[Decimal] = Field(None, ge=0, le=1, description="Fractional: 0.05 = 5%")
    service_charge_label: Optional[str] = Field(None, max_length=100)
    discount_rate: Optional[Decimal] = Field(None, ge=0, le=1, description="Fractional: 0.10 = 10%")
    currency: Optional[str] = Field(None, max_length=10)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _require_workspace(current_user: Dict[str, Any]) -> int:
    wid = current_user.get("workspace_id")
    if not wid:
        raise BadRequestError("workspace_id could not be resolved for this user")
    return wid


# ---------------------------------------------------------------------------
# GET /billing/overview
# ---------------------------------------------------------------------------

@router.get("/overview", response_model=BaseResponse)
async def get_billing_overview(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a complete billing overview for the UI dashboard:
    - Plan info (plan, status, next billing date, contact)
    - Legal/tax billing detail (GSTIN, PAN, address)
    - Transaction summary (total paid, pending count, last payment date)
    All 3 queries run in parallel.
    """
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "billing.overview.request user_id=%s workspace_id=%s",
        user_id, workspace_id,
    )

    overview = await BillingService(db).get_billing_overview(workspace_id)

    logger.info(
        "billing.overview.response user_id=%s workspace_id=%s plan=%s",
        user_id, workspace_id,
        overview.get("billing", {}).get("plan") if overview.get("billing") else None,
    )
    return {
        "success": True,
        "message": "Billing overview retrieved successfully",
        "data": overview,
    }


# ---------------------------------------------------------------------------
# GET /billing/config
# ---------------------------------------------------------------------------

@router.get("/config", response_model=BaseResponse)
async def get_billing_config(
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Get per-persona billing config (tax rate, service charge, discount, currency).
    Used by the order creation flow to pre-fill billing fields.
    """
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "billing.config.get.request user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )

    config = await BillingService(db).get_billing_config(workspace_id, persona_id)

    logger.info(
        "billing.config.get.response user_id=%s workspace_id=%s persona_id=%s found=%s",
        user_id, workspace_id, persona_id, config is not None,
    )
    return {
        "success": True,
        "message": "Billing config retrieved successfully",
        "data": config,
    }


# ---------------------------------------------------------------------------
# PUT /billing/config
# ---------------------------------------------------------------------------

@router.put("/config", response_model=BaseResponse)
async def upsert_billing_config(
    persona_id: int = Query(..., ge=1),
    body: UpsertBillingConfigRequest = ...,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Create or update per-persona billing config.
    Rates are fractional: 0.05 = 5%, 0.10 = 10%.
    """
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    data = body.model_dump(exclude_unset=True)

    if not data:
        logger.warning(
            "billing.config.upsert.empty_payload user_id=%s workspace_id=%s persona_id=%s",
            user_id, workspace_id, persona_id,
        )
        raise BadRequestError("No fields provided to update")

    logger.info(
        "billing.config.upsert.request user_id=%s workspace_id=%s persona_id=%s fields=%s",
        user_id, workspace_id, persona_id, list(data.keys()),
    )

    config = await BillingService(db).upsert_billing_config(workspace_id, persona_id, data)

    logger.info(
        "billing.config.upsert.response user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )
    return {
        "success": True,
        "message": "Billing config updated successfully",
        "data": config,
    }


# ---------------------------------------------------------------------------
# GET /billing/transactions
# ---------------------------------------------------------------------------

@router.get("/transactions", response_model=BaseResponse)
async def get_billing_transactions(
    payment_status: Optional[Literal["pending", "paid", "failed", "refunded"]] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated platform billing transactions for the caller's workspace."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "billing.transactions.request user_id=%s workspace_id=%s "
        "payment_status=%s page=%s page_size=%s",
        user_id, workspace_id, payment_status, page, page_size,
    )

    items, total, total_pages = await BillingService(db).get_billing_transactions(
        workspace_id=workspace_id,
        payment_status=payment_status,
        page=page,
        page_size=page_size,
    )

    logger.info(
        "billing.transactions.response user_id=%s workspace_id=%s "
        "total=%s page=%s returned=%s",
        user_id, workspace_id, total, page, len(items),
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


# ---------------------------------------------------------------------------
# GET /billing/due  — workspaces with billing due
# ---------------------------------------------------------------------------

@router.get("/due", response_model=BaseResponse)
async def get_billing_due_workspaces(
    overdue_only: bool = Query(False, description="If true, return only past-due workspaces"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Return paginated workspaces whose billing is due or overdue.

    - Default: workspaces where next_billing_date <= today
    - overdue_only=true: workspaces where next_billing_date < today (strictly past)

    Each row includes:
      workspace_id, workspace_name, plan, billing_email,
      next_billing_date, days_overdue, billing_cycle
    """
    user_id = current_user.get("id")

    logger.info(
        "billing.due.request user_id=%s overdue_only=%s page=%s page_size=%s",
        user_id, overdue_only, page, page_size,
    )

    items, total, total_pages = await BillingService(db).get_billing_due_workspaces(
        page=page,
        page_size=page_size,
        overdue_only=overdue_only,
    )

    logger.info(
        "billing.due.response user_id=%s total=%s overdue_only=%s page=%s returned=%s",
        user_id, total, overdue_only, page, len(items),
    )
    return {
        "success": True,
        "message": "Billing due workspaces retrieved successfully",
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
