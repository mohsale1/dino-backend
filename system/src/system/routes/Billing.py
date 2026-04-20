from fastapi import APIRouter, Body, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.system.services.Billing import BillingService
from src.system.services.Workspace import WorkspaceService
from src.base.BaseSchema import BaseResponse
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.config.Database import get_db
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter(prefix="/billing", tags=["System Billing"])

class UpdateSubscriptionRequest(BaseModel):
    plan: str
    status: str

@router.get("/workspaces", dependencies=[Depends(SystemPermissionCheck.require('billing:read'))])
async def get_all_billing_info(
    page: int = 1,
    page_size: int = 10,
    order_by: str = "created_at",
    order_direction: str = "desc",
    db: AsyncSession = Depends(get_db)
):
    """
    Get billing info for all workspaces with pagination (BillingManager, SuperAdmin)

    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    """
    billing_service = BillingService(db)

    # Validate page_size
    if page_size > 100:
        page_size = 100

    items, total, total_pages = await billing_service.get_paginated_billing_info(
        page=page,
        page_size=page_size,
        order_by=order_by,
        order_direction=order_direction
    )

    return {
        "success": True,
        "message": "Billing information retrieved successfully",
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

@router.get("/workspaces/{workspace_id}", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('billing:read'))])
async def get_workspace_billing(workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Get workspace billing information (BillingManager, SuperAdmin)"""
    billing_service = BillingService(db)

    billing_info = await billing_service.get_workspace_billing(workspace_id)

    if not billing_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    return {
        "success": True,
        "message": "Billing information retrieved successfully",
        "data": billing_info
    }

@router.put("/workspaces/{workspace_id}/subscription", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('billing:update'))])
async def update_subscription(workspace_id: int, request: UpdateSubscriptionRequest, db: AsyncSession = Depends(get_db)):
    """Update workspace subscription (BillingManager, SuperAdmin)"""
    billing_service = BillingService(db)

    success = await billing_service.update_subscription(workspace_id, request.plan, request.status)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    return {
        "success": True,
        "message": "Subscription updated successfully"
    }

@router.put("/workspaces/{workspace_id}/billing-info", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('billing:update'))])
async def update_billing_info(workspace_id: int, billing_info: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    """Update workspace billing information (BillingManager, SuperAdmin)"""
    workspace_service = WorkspaceService(db)

    success = await workspace_service.update_billing_info(workspace_id, billing_info)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    return {
        "success": True,
        "message": "Billing information updated successfully"
    }

@router.get("/stats", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('billing:read'))])
async def get_billing_stats(db: AsyncSession = Depends(get_db)):
    """Get billing statistics (BillingManager, SuperAdmin)"""
    billing_service = BillingService(db)

    stats = await billing_service.get_billing_stats()

    return {
        "success": True,
        "message": "Billing statistics retrieved successfully",
        "data": stats
    }
