"""
System Dashboard Routes
Provides endpoints for system-level analytics and statistics
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from src.core.Dependencies import get_current_system_user
from src.system.middleware.RoleCheck import SystemRoleCheck
from src.system.services.Dashboard import SystemDashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["System Dashboard"])


@router.get("", response_model=Dict[str, Any], dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_system_dashboard(
    current_user: Dict[str, Any] = Depends(get_current_system_user)
):
    """
    Get comprehensive system dashboard data

    Returns:
    - System statistics
    - Workspace growth trend
    - User distribution by role
    - Top user onboarders
    - Recent activity (last 24 hours)
    - Subscription stats
    - Registration code stats
    """
    try:
        stats = SystemDashboardService.get_system_stats()
        workspace_growth = SystemDashboardService.get_workspace_growth_trend(days=30)
        user_distribution = SystemDashboardService.get_user_distribution()
        top_onboarders = SystemDashboardService.get_top_onboarders(limit=5)
        recent_activity = SystemDashboardService.get_recent_activity(limit=20)
        subscription_stats = SystemDashboardService.get_subscription_stats()
        code_stats = SystemDashboardService.get_registration_code_stats()

        return {
            "success": True,
            "data": {
                "stats": stats,
                "workspace_growth": workspace_growth,
                "user_distribution": user_distribution,
                "top_onboarders": top_onboarders,
                "recent_activity": recent_activity,
                "subscription_stats": subscription_stats,
                "registration_code_stats": code_stats
            }
        }
    except Exception as e:
        logger.error("Failed to fetch dashboard data: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/stats", response_model=Dict[str, Any], dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_system_stats(
    current_user: Dict[str, Any] = Depends(get_current_system_user)
):
    """Get overall system statistics"""
    try:
        stats = SystemDashboardService.get_system_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error("Failed to fetch system stats: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/workspace-growth", response_model=Dict[str, Any], dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_workspace_growth(
    days: int = 30,
    current_user: Dict[str, Any] = Depends(get_current_system_user)
):
    """Get workspace growth trend"""
    try:
        growth_data = SystemDashboardService.get_workspace_growth_trend(days)
        return {
            "success": True,
            "data": growth_data
        }
    except Exception as e:
        logger.error("Failed to fetch workspace growth: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/user-distribution", response_model=Dict[str, Any], dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_user_distribution(
    current_user: Dict[str, Any] = Depends(get_current_system_user)
):
    """Get user distribution by role"""
    try:
        distribution = SystemDashboardService.get_user_distribution()
        return {
            "success": True,
            "data": distribution
        }
    except Exception as e:
        logger.error("Failed to fetch user distribution: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/top-onboarders", response_model=Dict[str, Any], dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_top_onboarders(
    limit: int = 5,
    current_user: Dict[str, Any] = Depends(get_current_system_user)
):
    """Get top user onboarders"""
    try:
        onboarders = SystemDashboardService.get_top_onboarders(limit)
        return {
            "success": True,
            "data": onboarders
        }
    except Exception as e:
        logger.error("Failed to fetch top onboarders: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/recent-activity", response_model=Dict[str, Any], dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def get_recent_activity(
    limit: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_system_user)
):
    """Get recent system activity (last 24 hours)"""
    try:
        activity = SystemDashboardService.get_recent_activity(limit)
        return {
            "success": True,
            "data": activity
        }
    except Exception as e:
        logger.error("Failed to fetch recent activity: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
