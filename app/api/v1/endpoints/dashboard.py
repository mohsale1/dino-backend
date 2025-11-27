"""
Dashboard API - Role-based analytics and insights
Access: Admin and SuperAdmin only
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

from app.core.security import get_current_user, _get_user_role
from app.core.logging import get_logger
from app.models.requests import ApiResponse

logger = get_logger(__name__)
router = APIRouter()


def _get_dashboard_service():
    """Lazy import to avoid circular dependencies"""
    from app.services.dashboard import DashboardService
    return DashboardService()


async def _require_admin_access(current_user: Dict[str, Any]) -> str:
    """Verify user has admin or superadmin role"""
    user_role = await _get_user_role(current_user)
    
    if user_role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or SuperAdmin role required for dashboard access."
        )
    
    return user_role


async def _get_user_venue_id(current_user: Dict[str, Any], user_role: str) -> Optional[str]:
    """Get venue ID for user (required for admin, optional for superadmin)"""
    venue_ids = current_user.get('venue_ids', [])
    
    # SuperAdmin can access all venues
    if user_role == "superadmin":
        return None
    
    # Admin must have at least one venue
    if not venue_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No venue assigned. Please contact your administrator."
        )
    
    # Return first venue as primary
    return venue_ids[0]


# =============================================================================
# CORE DASHBOARD ENDPOINTS
# =============================================================================

@router.get("", response_model=ApiResponse)
async def get_dashboard(
    venue_id: Optional[str] = Query(None, description="Specific venue ID (SuperAdmin only)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get dashboard data based on user role
    
    - **SuperAdmin**: System-wide overview or specific venue if venue_id provided
    - **Admin**: Venue-specific dashboard for assigned venue
    
    Access: Admin, SuperAdmin
    """
    try:
        user_role = await _require_admin_access(current_user)
        service = _get_dashboard_service()
        
        logger.info(f"Dashboard requested by user: {current_user.get('id')}, role: {user_role}")
        
        # SuperAdmin dashboard
        if user_role == "superadmin":
            if venue_id:
                # SuperAdmin viewing specific venue
                dashboard_data = await service.get_venue_dashboard(venue_id)
                message = f"Venue dashboard data retrieved successfully"
            else:
                # SuperAdmin system overview
                dashboard_data = await service.get_superadmin_dashboard()
                message = "SuperAdmin dashboard data retrieved successfully"
        
        # Admin dashboard
        else:
            user_venue_id = await _get_user_venue_id(current_user, user_role)
            dashboard_data = await service.get_venue_dashboard(user_venue_id)
            message = "Admin dashboard data retrieved successfully"
        
        return ApiResponse(
            success=True,
            message=message,
            data=dashboard_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard data"
        )


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/analytics", response_model=ApiResponse)
async def get_analytics(
    venue_id: Optional[str] = Query(None, description="Specific venue ID (SuperAdmin only)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get comprehensive analytics data
    
    - Revenue trends
    - Order statistics
    - Popular menu items
    - Performance metrics
    
    Access: Admin, SuperAdmin
    """
    try:
        user_role = await _require_admin_access(current_user)
        service = _get_dashboard_service()
        
        # Determine venue
        if user_role == "superadmin" and venue_id:
            target_venue_id = venue_id
        else:
            target_venue_id = await _get_user_venue_id(current_user, user_role)
        
        # Parse date range
        period_start, period_end = _parse_date_range(start_date, end_date)
        
        # Get analytics data
        analytics_data = await service.get_analytics(
            venue_id=target_venue_id,
            start_date=period_start,
            end_date=period_end
        )
        
        return ApiResponse(
            success=True,
            message="Analytics data retrieved successfully",
            data=analytics_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load analytics data"
        )


@router.get("/analytics/revenue", response_model=ApiResponse)
async def get_revenue_analytics(
    venue_id: Optional[str] = Query(None, description="Specific venue ID (SuperAdmin only)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    granularity: str = Query("day", regex="^(day|week|month)$", description="Data granularity"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get revenue analytics and trends
    
    - Revenue by period
    - Growth trends
    - Payment method breakdown
    - Average order value
    
    Access: Admin, SuperAdmin
    """
    try:
        user_role = await _require_admin_access(current_user)
        service = _get_dashboard_service()
        
        # Determine venue
        if user_role == "superadmin" and venue_id:
            target_venue_id = venue_id
        else:
            target_venue_id = await _get_user_venue_id(current_user, user_role)
        
        # Parse date range
        period_start, period_end = _parse_date_range(start_date, end_date)
        
        # Get revenue analytics
        revenue_data = await service.get_revenue_analytics(
            venue_id=target_venue_id,
            start_date=period_start,
            end_date=period_end,
            granularity=granularity
        )
        
        return ApiResponse(
            success=True,
            message="Revenue analytics retrieved successfully",
            data=revenue_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving revenue analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load revenue analytics"
        )


@router.get("/analytics/orders", response_model=ApiResponse)
async def get_order_analytics(
    venue_id: Optional[str] = Query(None, description="Specific venue ID (SuperAdmin only)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get order analytics and patterns
    
    - Order volume trends
    - Status breakdown
    - Peak hours analysis
    - Average preparation time
    
    Access: Admin, SuperAdmin
    """
    try:
        user_role = await _require_admin_access(current_user)
        service = _get_dashboard_service()
        
        # Determine venue
        if user_role == "superadmin" and venue_id:
            target_venue_id = venue_id
        else:
            target_venue_id = await _get_user_venue_id(current_user, user_role)
        
        # Parse date range
        period_start, period_end = _parse_date_range(start_date, end_date)
        
        # Get order analytics
        order_data = await service.get_order_analytics(
            venue_id=target_venue_id,
            start_date=period_start,
            end_date=period_end
        )
        
        return ApiResponse(
            success=True,
            message="Order analytics retrieved successfully",
            data=order_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving order analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load order analytics"
        )


@router.get("/analytics/menu", response_model=ApiResponse)
async def get_menu_analytics(
    venue_id: Optional[str] = Query(None, description="Specific venue ID (SuperAdmin only)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=50, description="Number of top items"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get menu performance analytics
    
    - Top selling items
    - Category performance
    - Item revenue contribution
    - Low performing items
    
    Access: Admin, SuperAdmin
    """
    try:
        user_role = await _require_admin_access(current_user)
        service = _get_dashboard_service()
        
        # Determine venue
        if user_role == "superadmin" and venue_id:
            target_venue_id = venue_id
        else:
            target_venue_id = await _get_user_venue_id(current_user, user_role)
        
        # Parse date range
        period_start, period_end = _parse_date_range(start_date, end_date)
        
        # Get menu analytics
        menu_data = await service.get_menu_analytics(
            venue_id=target_venue_id,
            start_date=period_start,
            end_date=period_end,
            limit=limit
        )
        
        return ApiResponse(
            success=True,
            message="Menu analytics retrieved successfully",
            data=menu_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving menu analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load menu analytics"
        )


# =============================================================================
# LIVE METRICS ENDPOINTS
# =============================================================================

@router.get("/live", response_model=ApiResponse)
async def get_live_metrics(
    venue_id: Optional[str] = Query(None, description="Specific venue ID (SuperAdmin only)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get real-time metrics for venue
    
    - Active orders count
    - Current revenue today
    - Table occupancy
    - Kitchen status
    
    Access: Admin, SuperAdmin
    """
    try:
        user_role = await _require_admin_access(current_user)
        service = _get_dashboard_service()
        
        # Determine venue
        if user_role == "superadmin" and venue_id:
            target_venue_id = venue_id
        else:
            target_venue_id = await _get_user_venue_id(current_user, user_role)
        
        # Get live metrics
        live_data = await service.get_live_metrics(target_venue_id)
        
        return ApiResponse(
            success=True,
            message="Live metrics retrieved successfully",
            data=live_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving live metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load live metrics"
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _parse_date_range(
    start_date: Optional[str],
    end_date: Optional[str]
) -> tuple[datetime, datetime]:
    """Parse and validate date range"""
    try:
        # Default to last 7 days if not provided
        if not start_date or not end_date:
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=7)
            return start, end
        
        # Parse provided dates
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
        
        # Validate date range
        if start > end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        # Limit to 1 year max
        if (end - start).days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date range cannot exceed 1 year"
            )
        
        return start, end
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )