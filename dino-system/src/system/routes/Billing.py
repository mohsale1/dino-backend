from fastapi import APIRouter, HTTPException, status, Depends
from src.system.services.Billing import BillingService
from src.base.BaseSchema import BaseResponse
from src.system.middleware.RoleCheck import SystemRoleCheck
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter(prefix="/billing", tags=["System Billing"])

class UpdateSubscriptionRequest(BaseModel):
    plan: str
    status: str

@router.get("/workspaces", dependencies=[Depends(SystemRoleCheck.require_billing_manager)])
async def get_all_billing_info(
    page: int = 1,
    page_size: int = 10,
    order_by: str = "created_at",
    order_direction: str = "desc"
):
    """
    Get billing info for all workspaces with pagination (BillingManager, SuperAdmin)
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - order_by: Field to order by (default: created_at)
    - order_direction: Order direction (asc/desc, default: desc)
    """
    service = BillingService()
    
    # Validate page_size
    if page_size > 100:
        page_size = 100
    
    items, total, total_pages = service.get_paginated_billing_info(
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

@router.get("/workspaces/{workspace_id}", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_billing_manager)])
async def get_workspace_billing(workspace_id: str):
    """Get workspace billing information (BillingManager, SuperAdmin)"""
    service = BillingService()
    
    billing_info = service.get_workspace_billing(workspace_id)
    
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

@router.put("/workspaces/{workspace_id}/subscription", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_billing_manager)])
async def update_subscription(workspace_id: str, request: UpdateSubscriptionRequest):
    """Update workspace subscription (BillingManager, SuperAdmin)"""
    service = BillingService()
    
    success = service.update_subscription(workspace_id, request.plan, request.status)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return {
        "success": True,
        "message": "Subscription updated successfully"
    }

@router.put("/workspaces/{workspace_id}/billing-info", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_billing_manager)])
async def update_billing_info(workspace_id: str, billing_info: Dict[str, Any]):
    """Update workspace billing information (BillingManager, SuperAdmin)"""
    from src.system.services.Workspace import WorkspaceService
    
    service = WorkspaceService()
    
    success = service.update_billing_info(workspace_id, billing_info)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    return {
        "success": True,
        "message": "Billing information updated successfully"
    }

@router.get("/stats", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_billing_manager)])
async def get_billing_stats():
    """Get billing statistics (BillingManager, SuperAdmin)"""
    service = BillingService()
    
    stats = service.get_billing_stats()
    
    return {
        "success": True,
        "message": "Billing statistics retrieved successfully",
        "data": stats
    }
