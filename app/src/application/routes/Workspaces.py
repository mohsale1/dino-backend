"""
Workspaces router — workspace info and billing management.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Billing import BillingService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.repositories.WorkspaceRepository import WorkspaceRepository

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class UpdateWorkspaceBillingRequest(BaseModel):
    plan: Optional[str] = None
    plan_status: Optional[str] = None
    billing_cycle: Optional[str] = None
    billing_email: Optional[str] = None
    billing_name: Optional[str] = None
    billing_address: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_country: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_phone: Optional[str] = None


class UpsertBillingDetailRequest(BaseModel):
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    billing_email: Optional[str] = None
    billing_phone: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/me", response_model=BaseResponse)
async def get_my_workspace(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's workspace."""
    workspace_id = current_user.get("workspace_id")
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not belong to a workspace",
        )
    repo = WorkspaceRepository(db)
    workspace = await repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return {"success": True, "message": "Workspace retrieved successfully", "data": workspace}


@router.get("/{workspace_id}", response_model=BaseResponse)
async def get_workspace(
    workspace_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("workspaces:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a workspace by ID."""
    repo = WorkspaceRepository(db)
    workspace = await repo.get_by_id(workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return {"success": True, "message": "Workspace retrieved successfully", "data": workspace}


@router.put("/{workspace_id}", response_model=BaseResponse)
async def update_workspace(
    workspace_id: int,
    request: UpdateWorkspaceRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("workspaces:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update workspace details."""
    repo = WorkspaceRepository(db)
    existing = await repo.get_by_id(workspace_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    data = request.model_dump(exclude_unset=True)
    success = await repo.update(workspace_id, data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return {"success": True, "message": "Workspace updated successfully"}


@router.get("/{workspace_id}/billing", response_model=BaseResponse)
async def get_workspace_billing(
    workspace_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("billing:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get workspace billing plan info."""
    service = BillingService(db)
    billing = await service.get_workspace_billing(workspace_id)
    if not billing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing info not found")
    return {"success": True, "message": "Billing retrieved successfully", "data": billing}


@router.put("/{workspace_id}/billing", response_model=BaseResponse)
async def update_workspace_billing(
    workspace_id: int,
    request: UpdateWorkspaceBillingRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("billing:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update workspace billing plan info."""
    service = BillingService(db)
    data = request.model_dump(exclude_unset=True)
    result = await service.update_workspace_billing(workspace_id, data)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing info not found")
    return {"success": True, "message": "Billing updated successfully", "data": result}


@router.get("/{workspace_id}/billing-detail", response_model=BaseResponse)
async def get_billing_detail(
    workspace_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("billing:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get billing details (GST/tax info) for a workspace."""
    service = BillingService(db)
    detail = await service.get_billing_detail(workspace_id)
    return {"success": True, "message": "Billing detail retrieved successfully", "data": detail}


@router.put("/{workspace_id}/billing-detail", response_model=BaseResponse)
async def upsert_billing_detail(
    workspace_id: int,
    request: UpsertBillingDetailRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("billing:update")),
    db: AsyncSession = Depends(get_db),
):
    """Create or update billing details for a workspace."""
    service = BillingService(db)
    data = request.model_dump(exclude_unset=True)
    result = await service.create_or_update_billing_detail(workspace_id, data)
    return {"success": True, "message": "Billing detail updated successfully", "data": result}


@router.get("/{workspace_id}/billing-transactions", response_model=BaseResponse)
async def get_billing_transactions(
    workspace_id: int,
    payment_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("billing:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated billing transactions for a workspace."""
    service = BillingService(db)
    items, total, total_pages = await service.get_billing_transactions(
        workspace_id=workspace_id,
        payment_status=payment_status,
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
