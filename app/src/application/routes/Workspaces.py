"""
Workspaces router — workspace info and billing management.
All endpoints are scoped to the caller's own workspace via _assert_own_workspace.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Billing import BillingService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError, WorkspaceMismatchError
from src.repositories.WorkspaceRepository import WorkspaceRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class UpdateWorkspaceBillingRequest(BaseModel):
    billing_cycle: Optional[str] = Field(None, max_length=50)
    billing_email: Optional[str] = Field(None, max_length=320)
    billing_name: Optional[str] = Field(None, max_length=200)
    billing_address: Optional[str] = Field(None, max_length=500)
    billing_city: Optional[str] = Field(None, max_length=100)
    billing_state: Optional[str] = Field(None, max_length=100)
    billing_country: Optional[str] = Field(None, max_length=100)
    billing_postal_code: Optional[str] = Field(None, max_length=20)
    billing_phone: Optional[str] = Field(None, max_length=30)


class UpsertBillingDetailRequest(BaseModel):
    legal_name: Optional[str] = Field(None, max_length=200)
    trade_name: Optional[str] = Field(None, max_length=200)
    gstin: Optional[str] = Field(None, max_length=15)
    pan: Optional[str] = Field(None, max_length=10)
    billing_email: Optional[EmailStr] = None
    billing_phone: Optional[str] = Field(None, max_length=30)
    address_line1: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _assert_own_workspace(workspace_id: int, current_user: Dict[str, Any]) -> None:
    if workspace_id != current_user.get("workspace_id"):
        raise WorkspaceMismatchError()


# ---------------------------------------------------------------------------
# GET /workspaces/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=BaseResponse)
async def get_my_workspace(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's workspace."""
    user_id = current_user.get("id")
    workspace_id = current_user.get("workspace_id")

    logger.info("workspaces.me.request user_id=%s workspace_id=%s", user_id, workspace_id)

    if not workspace_id:
        raise NotFoundError("User does not belong to a workspace")

    workspace = await WorkspaceRepository(db).get_by_id(workspace_id)
    if not workspace:
        raise NotFoundError("Workspace not found")

    logger.info(
        "workspaces.me.response user_id=%s workspace_id=%s name=%r",
        user_id, workspace_id, workspace.get("name"),
    )
    return {"success": True, "message": "Workspace retrieved successfully", "data": workspace}


# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_id}
# ---------------------------------------------------------------------------

@router.get("/{workspace_id}", response_model=BaseResponse)
async def get_workspace(
    workspace_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a workspace by ID — must be the caller's own workspace."""
    user_id = current_user.get("id")
    _assert_own_workspace(workspace_id, current_user)

    logger.info("workspaces.get.request user_id=%s workspace_id=%s", user_id, workspace_id)

    workspace = await WorkspaceRepository(db).get_by_id(workspace_id)
    if not workspace:
        raise NotFoundError("Workspace not found")

    logger.info(
        "workspaces.get.response user_id=%s workspace_id=%s name=%r",
        user_id, workspace_id, workspace.get("name"),
    )
    return {"success": True, "message": "Workspace retrieved successfully", "data": workspace}


# ---------------------------------------------------------------------------
# PUT /workspaces/{workspace_id}
# ---------------------------------------------------------------------------

@router.put("/{workspace_id}", response_model=BaseResponse)
async def update_workspace(
    workspace_id: int,
    request: UpdateWorkspaceRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update workspace name/description — single round-trip UPDATE."""
    user_id = current_user.get("id")
    _assert_own_workspace(workspace_id, current_user)

    data = request.model_dump(exclude_unset=True)
    if not data:
        logger.warning("workspaces.update.empty_payload user_id=%s workspace_id=%s", user_id, workspace_id)
        raise BadRequestError("No fields provided for update")

    logger.info(
        "workspaces.update.request user_id=%s workspace_id=%s fields=%s",
        user_id, workspace_id, list(data.keys()),
    )

    success = await WorkspaceRepository(db).update(workspace_id, data)
    if not success:
        raise NotFoundError("Workspace not found")

    logger.info(
        "workspaces.update.response user_id=%s workspace_id=%s fields=%s",
        user_id, workspace_id, list(data.keys()),
    )
    return {"success": True, "message": "Workspace updated successfully"}


# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_id}/billing
# ---------------------------------------------------------------------------

@router.get("/{workspace_id}/billing", response_model=BaseResponse)
async def get_workspace_billing(
    workspace_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get workspace billing plan info."""
    user_id = current_user.get("id")
    _assert_own_workspace(workspace_id, current_user)

    logger.info("workspaces.billing.get.request user_id=%s workspace_id=%s", user_id, workspace_id)

    billing = await BillingService(db).get_workspace_billing(workspace_id)
    if not billing:
        raise NotFoundError("Billing info not found")

    logger.info("workspaces.billing.get.response user_id=%s workspace_id=%s", user_id, workspace_id)
    return {"success": True, "message": "Billing retrieved successfully", "data": billing}


# ---------------------------------------------------------------------------
# PUT /workspaces/{workspace_id}/billing
# ---------------------------------------------------------------------------

@router.put("/{workspace_id}/billing", response_model=BaseResponse)
async def update_workspace_billing(
    workspace_id: int,
    request: UpdateWorkspaceBillingRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update workspace billing plan info."""
    user_id = current_user.get("id")
    _assert_own_workspace(workspace_id, current_user)

    data = request.model_dump(exclude_unset=True)
    if not data:
        logger.warning("workspaces.billing.update.empty_payload user_id=%s workspace_id=%s", user_id, workspace_id)
        raise BadRequestError("No fields provided for update")

    logger.info(
        "workspaces.billing.update.request user_id=%s workspace_id=%s fields=%s",
        user_id, workspace_id, list(data.keys()),
    )

    result = await BillingService(db).update_workspace_billing(workspace_id, data)
    if not result:
        raise NotFoundError("Billing info not found")

    logger.info("workspaces.billing.update.response user_id=%s workspace_id=%s", user_id, workspace_id)
    return {"success": True, "message": "Billing updated successfully", "data": result}


# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_id}/billing-detail
# ---------------------------------------------------------------------------

@router.get("/{workspace_id}/billing-detail", response_model=BaseResponse)
async def get_billing_detail(
    workspace_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get billing details (GST/tax info) for a workspace."""
    user_id = current_user.get("id")
    _assert_own_workspace(workspace_id, current_user)

    logger.info("workspaces.billing_detail.get.request user_id=%s workspace_id=%s", user_id, workspace_id)

    detail = await BillingService(db).get_billing_detail(workspace_id)

    logger.info("workspaces.billing_detail.get.response user_id=%s workspace_id=%s", user_id, workspace_id)
    return {"success": True, "message": "Billing detail retrieved successfully", "data": detail}


# ---------------------------------------------------------------------------
# PUT /workspaces/{workspace_id}/billing-detail
# ---------------------------------------------------------------------------

@router.put("/{workspace_id}/billing-detail", response_model=BaseResponse)
async def upsert_billing_detail(
    workspace_id: int,
    request: UpsertBillingDetailRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Create or update billing details for a workspace."""
    user_id = current_user.get("id")
    _assert_own_workspace(workspace_id, current_user)

    data = request.model_dump(exclude_unset=True)
    logger.info(
        "workspaces.billing_detail.upsert.request user_id=%s workspace_id=%s fields=%s",
        user_id, workspace_id, list(data.keys()),
    )

    result = await BillingService(db).create_or_update_billing_detail(workspace_id, data)

    logger.info("workspaces.billing_detail.upsert.response user_id=%s workspace_id=%s", user_id, workspace_id)
    return {"success": True, "message": "Billing detail updated successfully", "data": result}


# ---------------------------------------------------------------------------
# GET /workspaces/{workspace_id}/billing-transactions
# ---------------------------------------------------------------------------

@router.get("/{workspace_id}/billing-transactions", response_model=BaseResponse)
async def get_billing_transactions(
    workspace_id: int,
    payment_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated billing transactions for a workspace."""
    user_id = current_user.get("id")
    _assert_own_workspace(workspace_id, current_user)

    logger.info(
        "workspaces.billing_transactions.request user_id=%s workspace_id=%s "
        "payment_status=%s page=%s page_size=%s",
        user_id, workspace_id, payment_status, page, page_size,
    )

    items, total, total_pages = await BillingService(db).get_billing_transactions(
        workspace_id=workspace_id,
        payment_status=payment_status,
        page=page,
        page_size=page_size,
    )

    # Add index field
    offset = (page - 1) * page_size
    for idx, item in enumerate(items, start=offset + 1):
        item["index"] = idx

    logger.info(
        "workspaces.billing_transactions.response user_id=%s workspace_id=%s "
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
# GET /workspaces/{workspace_id}/approval-status
# ---------------------------------------------------------------------------

@router.get("/{workspace_id}/approval-status", response_model=BaseResponse)
async def get_workspace_approval_status(
    workspace_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Check the approval status of a workspace request."""
    user_id = current_user.get("id")
    _assert_own_workspace(workspace_id, current_user)

    logger.info(
        "workspaces.approval_status.request user_id=%s workspace_id=%s",
        user_id, workspace_id,
    )

    result = await db.execute(
        sa_text(
            "SELECT id, status, reviewed_at, rejection_reason "
            "FROM workspace_requests "
            "WHERE workspace_id = :wid AND is_active = true "
            "ORDER BY created_at DESC "
            "LIMIT 1"
        ),
        {"wid": workspace_id},
    )
    row = result.mappings().first()

    if row is None:
        logger.info(
            "workspaces.approval_status.no_request user_id=%s workspace_id=%s",
            user_id, workspace_id,
        )
        return {
            "success": True,
            "message": "No workspace request found",
            "data": {
                "workspace_id": workspace_id,
                "request_exists": False,
                "approved": False,
                "status": None,
                "reviewed_at": None,
                "rejection_reason": None,
            },
        }

    req_status = row["status"]
    logger.info(
        "workspaces.approval_status.response user_id=%s workspace_id=%s status=%s",
        user_id, workspace_id, req_status,
    )
    return {
        "success": True,
        "message": "Workspace request status retrieved successfully",
        "data": {
            "workspace_id": workspace_id,
            "request_exists": True,
            "approved": req_status == "approved",
            "status": req_status,
            "reviewed_at": str(row["reviewed_at"]) if row["reviewed_at"] else None,
            "rejection_reason": row["rejection_reason"],
        },
    }
