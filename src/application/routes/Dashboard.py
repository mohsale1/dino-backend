from fastapi import APIRouter, HTTPException, status, Depends, Query
from src.application.services.Dashboard import DashboardService
from src.base.BaseSchema import BaseResponse
from src.application.middleware.RoleCheck import ApplicationRoleCheck
from typing import Optional, Dict, Any

router = APIRouter(prefix="/dashboard", tags=["Application Dashboard"])

@router.get("", dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_dashboard(
    workspace_id: str = Query(..., description="Workspace ID"),
    organization_id: Optional[str] = Query(None, description="Organization ID (optional)"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """
    Get comprehensive dashboard data
    
    Query Parameters:
    - workspace_id: Workspace ID (required)
    - organization_id: Organization ID for filtering (optional)
    - start_date: Start date for filtering data (ISO format, optional)
    - end_date: End date for filtering data (ISO format, optional)
    
    Returns comprehensive dashboard data including:
    - Statistics (revenue, orders, tables, items)
    - Analytics (revenue trend, order status, popular items, category performance)
    - Recent activity
    - Table statuses
    """
    service = DashboardService()
    
    try:
        # Get user's role for access control
        user_role = user.get('role', {}).get('name')
        
        # If user is Manager or Operator, ensure they can only see their organization's data
        if user_role in ['Manager', 'Operator']:
            user_org_id = user.get('organization_id')
            if organization_id and organization_id != user_org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization's data"
                )
            # Force organization filter for non-admin users
            organization_id = user_org_id
        
        dashboard_data = service.get_venue_dashboard(
            workspace_id=workspace_id,
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return dashboard_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard data: {str(e)}"
        )

@router.get("/stats", dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_dashboard_stats(
    workspace_id: str = Query(..., description="Workspace ID"),
    organization_id: Optional[str] = Query(None, description="Organization ID (optional)"),
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """
    Get dashboard statistics only (lightweight endpoint)
    
    Query Parameters:
    - workspace_id: Workspace ID (required)
    - organization_id: Organization ID for filtering (optional)
    """
    service = DashboardService()
    
    try:
        # Get user's role for access control
        user_role = user.get('role', {}).get('name')
        
        # If user is Manager or Operator, ensure they can only see their organization's data
        if user_role in ['Manager', 'Operator']:
            user_org_id = user.get('organization_id')
            if organization_id and organization_id != user_org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization's data"
                )
            organization_id = user_org_id
        
        dashboard_data = service.get_venue_dashboard(
            workspace_id=workspace_id,
            organization_id=organization_id
        )
        
        # Return only stats and summary
        return {
            "success": True,
            "data": {
                "stats": dashboard_data["data"]["stats"],
                "summary": dashboard_data["data"]["summary"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard stats: {str(e)}"
        )

@router.get("/analytics", dependencies=[Depends(ApplicationRoleCheck.require_operator)])
async def get_dashboard_analytics(
    workspace_id: str = Query(..., description="Workspace ID"),
    organization_id: Optional[str] = Query(None, description="Organization ID (optional)"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    user: Dict[str, Any] = Depends(ApplicationRoleCheck.require_operator)
):
    """
    Get dashboard analytics only
    
    Query Parameters:
    - workspace_id: Workspace ID (required)
    - organization_id: Organization ID for filtering (optional)
    - start_date: Start date for filtering data (ISO format, optional)
    - end_date: End date for filtering data (ISO format, optional)
    """
    service = DashboardService()
    
    try:
        # Get user's role for access control
        user_role = user.get('role', {}).get('name')
        
        # If user is Manager or Operator, ensure they can only see their organization's data
        if user_role in ['Manager', 'Operator']:
            user_org_id = user.get('organization_id')
            if organization_id and organization_id != user_org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization's data"
                )
            organization_id = user_org_id
        
        dashboard_data = service.get_venue_dashboard(
            workspace_id=workspace_id,
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Return only analytics
        return {
            "success": True,
            "data": dashboard_data["data"]["analytics"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard analytics: {str(e)}"
        )