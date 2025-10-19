"""
Dashboard endpoints for different user roles
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.core.security import get_current_user
from app.core.logging_config import get_logger
from app.models.dto import ApiResponse
# Dashboard service imported lazily to avoid circular imports

logger = get_logger(__name__)

router = APIRouter()


def _get_dashboard_service():
    """Lazy import of dashboard service to avoid circular imports"""
    from app.services.dashboard_service import dashboard_service
    return dashboard_service


@router.get("/dashboard/superadmin", response_model=ApiResponse)
async def get_superadmin_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get super admin dashboard data"""
    logger.info(f"Super admin dashboard requested by user: {current_user.get('id')}")
    
    # Get user role from role_id
    from app.core.security import _get_user_role
    user_role = await _get_user_role(current_user)
    
    # Check if user has superadmin role
    if user_role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Super admin role required."
        )
    
    try:
        # Get system-wide data and format it for UI
        system_data = await _get_dashboard_service().get_superadmin_dashboard_data(current_user)
        
        # Transform to match UI expectations (SuperAdminDashboardResponse format)
        dashboard_data = {
            "system_stats": system_data["system_stats"],
            "workspaces": system_data.get("workspaces", []),
            "venue_performance": system_data.get("venue_performance", []),
            "top_menu_items": system_data.get("top_menu_items", []),
            "recent_activity": system_data.get("recent_activity", []),
            "analytics": system_data.get("analytics", {
                "order_status_breakdown": {},
                "table_status_breakdown": {},
                "revenue_by_venue": {}
            }),
            "is_superadmin_view": True,
            "current_venue_id": None
        }
        
        logger.info(f"Super admin dashboard data retrieved for user: {current_user.get('id')}")
        
        return ApiResponse(
            success=True,
            message="Super admin dashboard data retrieved successfully",
            data=dashboard_data
        )
    except Exception as e:
        logger.error(f"Error retrieving super admin dashboard data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard data"
        )


@router.get("/dashboard/admin", response_model=ApiResponse)
async def get_admin_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get admin dashboard data for venue"""
    logger.info(f"Admin dashboard requested by user: {current_user.get('id')}")
    
    # Get user role from role_id
    from app.core.security import _get_user_role
    user_role = await _get_user_role(current_user)
    
    # Check if user has admin role
    if user_role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    # Check if user has venue assigned (except for superadmin)
    venue_ids = current_user.get('venue_ids', [])
    venue_id = venue_ids[0] if venue_ids else None
    
    if user_role != "superadmin" and not venue_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No venue assigned. Please contact your administrator to assign you to a venue."
        )
    
    try:
        dashboard_data = await _get_dashboard_service().get_admin_dashboard_data(venue_id, current_user)
        logger.info(f"Admin dashboard data retrieved for user: {current_user.get('id')}, venue: {venue_id}")
        
        return ApiResponse(
            success=True,
            message="Admin dashboard data retrieved successfully",
            data=dashboard_data
        )
    except Exception as e:
        logger.error(f"Error retrieving admin dashboard data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard data"
        )


@router.get("/dashboard/operator", response_model=ApiResponse)
async def get_operator_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get operator dashboard data for venue"""
    logger.info(f"Operator dashboard requested by user: {current_user.get('id')}")
    
    # Get user role from role_id
    from app.core.security import _get_user_role
    user_role = await _get_user_role(current_user)
    
    # Check if user has operator role
    if user_role not in ["operator", "admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Operator role required."
        )
    
    # Check if user has venue assigned (except for superadmin)
    venue_ids = current_user.get('venue_ids', [])
    venue_id = venue_ids[0] if venue_ids else None
    
    if user_role != "superadmin" and not venue_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No venue assigned. Please contact your administrator to assign you to a venue."
        )
    
    try:
        dashboard_data = await _get_dashboard_service().get_operator_dashboard_data(venue_id, current_user)
        logger.info(f"Operator dashboard data retrieved for user: {current_user.get('id')}, venue: {venue_id}")
        
        return ApiResponse(
            success=True,
            message="Operator dashboard data retrieved successfully",
            data=dashboard_data
        )
    except Exception as e:
        logger.error(f"Error retrieving operator dashboard data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard data"
        )


@router.get("/dashboard", response_model=ApiResponse)
async def get_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get dashboard data based on user role"""
    logger.info(f"Dashboard requested by user: {current_user.get('id')}")
    
    try:
        # Get user role from role_id
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        venue_ids = current_user.get('venue_ids', [])
        venue_id = venue_ids[0] if venue_ids else None
        
        logger.info(f"Dashboard requested by user: {current_user.get('id')}, role: {user_role}")
        
        # Route to appropriate dashboard based on role
        if user_role == "superadmin":
            dashboard_data = await _get_dashboard_service().get_superadmin_dashboard_data(current_user)
        elif user_role == "admin":
            # Check if user has venue assigned
            if not venue_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No venue assigned. Please contact your administrator to assign you to a venue."
                )
            dashboard_data = await _get_dashboard_service().get_admin_dashboard_data(venue_id, current_user)
        elif user_role == "operator":
            # Check if user has venue assigned
            if not venue_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No venue assigned. Please contact your administrator to assign you to a venue."
                )
            dashboard_data = await _get_dashboard_service().get_operator_dashboard_data(venue_id, current_user)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Dashboard access not available for your role."
            )
        
        return ApiResponse(
            success=True,
            message=f"{user_role.title()} dashboard data retrieved successfully",
            data=dashboard_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving dashboard data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard data"
        )


@router.get("/dashboard/stats", response_model=ApiResponse)
async def get_dashboard_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get general dashboard statistics"""
    logger.info(f"Dashboard stats requested by user: {current_user.get('id')}")
    
    try:
        # Get user role from role_id
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        venue_ids = current_user.get('venue_ids', [])
        venue_id = venue_ids[0] if venue_ids else None
        
        # Return basic stats that can be used across different dashboards
        stats = {
            "user_id": current_user.get('id'),
            "user_role": user_role,
            "venue_id": venue_id,
            "workspace_id": current_user.get('workspace_id'),
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        # Add role-specific stats
        if venue_id:
            venue_data = await _get_dashboard_service().get_admin_dashboard_data(venue_id, current_user)
            stats.update({
                "today_orders": venue_data["summary"]["today_orders"],
                "today_revenue": venue_data["summary"]["today_revenue"],
                "occupied_tables": venue_data["summary"]["occupied_tables"],
                "total_tables": venue_data["summary"]["total_tables"],
            })
        
        return ApiResponse(
            success=True,
            message="Dashboard statistics retrieved successfully",
            data=stats
        )
    except Exception as e:
        logger.error(f"Error retrieving dashboard stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard statistics"
        )


@router.get("/dashboard/live-orders/{venue_id}", response_model=ApiResponse)
async def get_live_order_status(venue_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get live order status for a venue"""
    logger.info(f"Live order status requested for venue: {venue_id} by user: {current_user.get('id')}")
    
    # Get user role from role_id
    from app.core.security import _get_user_role
    user_role = await _get_user_role(current_user)
    
    # Check permissions
    if user_role not in ["admin", "operator", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or operator role required."
        )
    
    # Check venue access (except for superadmin)
    user_venue_ids = current_user.get('venue_ids', [])
    if user_role != "superadmin" and venue_id not in user_venue_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view data for your assigned venue."
        )
    
    try:
        live_data = await _get_dashboard_service().get_live_order_status(venue_id)
        
        return ApiResponse(
            success=True,
            message="Live order status retrieved successfully",
            data=live_data
        )
    except Exception as e:
        logger.error(f"Error retrieving live order status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load live order status"
        )


@router.get("/dashboard/live-tables/{venue_id}", response_model=ApiResponse)
async def get_live_table_status(venue_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get live table status for a venue"""
    logger.info(f"Live table status requested for venue: {venue_id} by user: {current_user.get('id')}")
    
    # Get user role from role_id
    from app.core.security import _get_user_role
    user_role = await _get_user_role(current_user)
    
    # Check permissions
    if user_role not in ["admin", "operator", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or operator role required."
        )
    
    # Check venue access (except for superadmin)
    user_venue_ids = current_user.get('venue_ids', [])
    if user_role != "superadmin" and venue_id not in user_venue_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view data for your assigned venue."
        )
    
    try:
        live_data = await _get_dashboard_service().get_live_table_status(venue_id)
        
        return ApiResponse(
            success=True,
            message="Live table status retrieved successfully",
            data=live_data
        )
    except Exception as e:
        logger.error(f"Error retrieving live table status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load live table status"
        )


@router.get("/dashboard/venue/{venue_id}", response_model=ApiResponse)
async def get_venue_dashboard(venue_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get dashboard data for a specific venue with enhanced data for SuperAdmin"""
    logger.info(f"Venue dashboard requested for venue: {venue_id} by user: {current_user.get('id')}")
    
    # Get user role from role_id
    from app.core.security import _get_user_role
    user_role = await _get_user_role(current_user)
    
    # Check permissions
    if user_role not in ["admin", "operator", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or operator role required."
        )
    
    # Check venue access (except for superadmin)
    user_venue_ids = current_user.get('venue_ids', [])
    if user_role != "superadmin" and venue_id not in user_venue_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view data for your assigned venue."
        )
    
    try:
        # Both Admin and SuperAdmin get venue-specific data
        # SuperAdmin gets data in UI-expected format, Admin gets regular venue data
        if user_role == "superadmin":
            dashboard_data = await _get_dashboard_service().get_superadmin_enhanced_venue_data(venue_id, current_user)
        else:
            dashboard_data = await _get_dashboard_service().get_venue_dashboard_data(venue_id, current_user)
        
        return ApiResponse(
            success=True,
            message="Venue dashboard data retrieved successfully",
            data=dashboard_data
        )
    except Exception as e:
        logger.error(f"Error retrieving venue dashboard data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load venue dashboard data"
        )


@router.get("/dashboard/comprehensive", response_model=ApiResponse)
async def get_comprehensive_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get comprehensive dashboard data for admin users"""
    logger.info(f"Comprehensive dashboard requested by user: {current_user.get('id')}")
    
    # Get user role from role_id
    from app.core.security import _get_user_role
    user_role = await _get_user_role(current_user)
    
    # Check if user has admin role
    if user_role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required."
        )
    
    # Check if user has venue assigned (except for superadmin)
    venue_ids = current_user.get('venue_ids', [])
    venue_id = venue_ids[0] if venue_ids else None
    
    logger.info(f"User {current_user.get('id')} has venue_ids: {venue_ids}, using venue_id: {venue_id}")
    
    if user_role != "superadmin" and not venue_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No venue assigned. Please contact your administrator to assign you to a venue."
        )
    
    try:
        # Get comprehensive dashboard data using the new service method
        comprehensive_data = await _get_dashboard_service().get_comprehensive_dashboard_data(venue_id, current_user)
        
        return ApiResponse(
            success=True,
            message="Comprehensive dashboard data retrieved successfully",
            data=comprehensive_data
        )
    except Exception as e:
        logger.error(f"Error retrieving comprehensive dashboard data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load comprehensive dashboard data"
        )


def _get_status_color(status: str) -> str:
    """Get color for order status"""
    colors = {
        "pending": "#FFF176",
        "confirmed": "#FFCC02", 
        "preparing": "#81D4FA",
        "ready": "#C8E6C9",
        "served": "#E1BEE7",
        "delivered": "#A5D6A7",
        "cancelled": "#FFAB91"
    }
    return colors.get(status.lower(), "#F5F5F5")


def _get_table_status_color(status: str) -> str:
    """Get color for table status"""
    colors = {
        "available": "#A5D6A7",
        "occupied": "#FFAB91",
        "reserved": "#81D4FA",
        "maintenance": "#FFCC02"
    }
    return colors.get(status.lower(), "#F5F5F5")


@router.get("/dashboard/superadmin/comprehensive", response_model=ApiResponse)
async def get_superadmin_comprehensive_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get comprehensive dashboard data for superadmin users"""
    logger.info(f"SuperAdmin comprehensive dashboard requested by user: {current_user.get('id')}")
    
    # Get user role from role_id
    from app.core.security import _get_user_role
    user_role = await _get_user_role(current_user)
    
    # Check if user has superadmin role
    if user_role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Super admin role required."
        )
    
    try:
        dashboard_data = await _get_dashboard_service().get_superadmin_dashboard_data(current_user)
        
        # Transform data to match frontend expectations
        comprehensive_data = {
            "system_stats": {
                "total_workspaces": dashboard_data["summary"]["total_workspaces"],
                "total_venues": dashboard_data["summary"]["total_venues"],
                "total_users": dashboard_data["summary"]["total_users"],
                "total_orders": dashboard_data["summary"]["total_orders"],
                "total_revenue": dashboard_data["summary"]["total_revenue"],
                "active_venues": dashboard_data["summary"]["active_venues"],
                "total_orders_today": 0,  # Would need to be calculated
                "total_revenue_today": 0.0  # Would need to be calculated
            },
            "workspaces": dashboard_data["workspaces"],
            "recent_activity": [],  # Could be populated with recent system activity
            "growth_metrics": {}    # Could be populated with growth data
        }
        
        return ApiResponse(
            success=True,
            message="SuperAdmin comprehensive dashboard data retrieved successfully",
            data=comprehensive_data
        )
    except Exception as e:
        logger.error(f"Error retrieving superadmin comprehensive dashboard data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load superadmin comprehensive dashboard data"
        )


@router.get("/dashboard/operator/comprehensive", response_model=ApiResponse)
async def get_operator_comprehensive_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get comprehensive dashboard data for operator users"""
    logger.info(f"Operator comprehensive dashboard requested by user: {current_user.get('id')}")
    
    # Get user role from role_id
    from app.core.security import _get_user_role
    user_role = await _get_user_role(current_user)
    
    # Check if user has operator role
    if user_role not in ["operator", "admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Operator role required."
        )
    
    # Check if user has venue assigned (except for superadmin)
    venue_ids = current_user.get('venue_ids', [])
    venue_id = venue_ids[0] if venue_ids else None
    
    if user_role != "superadmin" and not venue_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No venue assigned. Please contact your administrator to assign you to a venue."
        )
    
    try:
        dashboard_data = await _get_dashboard_service().get_operator_dashboard_data(venue_id, current_user)
        
        # Transform data to match frontend expectations
        comprehensive_data = {
            "venue_name": "Current Venue",  # Would need venue name from venue data
            "venue_id": venue_id,
            "stats": {
                "active_orders": dashboard_data["summary"]["active_orders"],
                "pending_orders": dashboard_data["summary"]["pending_orders"],
                "preparing_orders": dashboard_data["summary"]["preparing_orders"],
                "ready_orders": dashboard_data["summary"]["ready_orders"],
                "tables_occupied": dashboard_data["summary"]["occupied_tables"],
                "tables_total": dashboard_data["summary"]["total_tables"]
            },
            "active_orders": dashboard_data["active_orders"],
            "order_queue": dashboard_data["active_orders"],  # Same as active orders for operators
            "table_status": {
                "occupied": dashboard_data["summary"]["occupied_tables"],
                "available": dashboard_data["summary"]["total_tables"] - dashboard_data["summary"]["occupied_tables"]
            }
        }
        
        return ApiResponse(
            success=True,
            message="Operator comprehensive dashboard data retrieved successfully",
            data=comprehensive_data
        )
    except Exception as e:
        logger.error(f"Error retrieving operator comprehensive dashboard data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load operator comprehensive dashboard data"
        )