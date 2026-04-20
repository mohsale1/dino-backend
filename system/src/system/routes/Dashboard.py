"""
System Dashboard Routes
Provides endpoints for system-level analytics and statistics
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.Dashboard import SystemDashboardService
from src.config.Database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["System Dashboard"])


@router.get("", response_model=Dict[str, Any], dependencies=[Depends(SystemPermissionCheck.require('dashboard:read'))])
async def get_system_dashboard(
    current_user: Dict[str, Any] = Depends(SystemPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db)
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
    """
    try:
        service = SystemDashboardService(db)
        stats = await service.get_system_stats()
        workspace_growth = await service.get_workspace_growth_trend(days=30)
        user_distribution = await service.get_user_distribution()
        top_onboarders = await service.get_top_onboarders(limit=5)
        recent_activity = await service.get_recent_activity(limit=20)
        subscription_stats = await service.get_subscription_stats()

        return {
            "success": True,
            "data": {
                "stats": stats,
                "workspace_growth": workspace_growth,
                "user_distribution": user_distribution,
                "top_onboarders": top_onboarders,
                "recent_activity": recent_activity,
                "subscription_stats": subscription_stats,
            }
        }
    except Exception as e:
        logger.error("Failed to fetch dashboard data: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/stats", response_model=Dict[str, Any], dependencies=[Depends(SystemPermissionCheck.require('dashboard:read'))])
async def get_system_stats(
    current_user: Dict[str, Any] = Depends(SystemPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db)
):
    """Get overall system statistics"""
    try:
        service = SystemDashboardService(db)
        stats = await service.get_system_stats()
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


@router.get("/workspace-growth", response_model=Dict[str, Any], dependencies=[Depends(SystemPermissionCheck.require('dashboard:read'))])
async def get_workspace_growth(
    days: int = 30,
    current_user: Dict[str, Any] = Depends(SystemPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db)
):
    """Get workspace growth trend"""
    try:
        service = SystemDashboardService(db)
        growth_data = await service.get_workspace_growth_trend(days)
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


@router.get("/user-distribution", response_model=Dict[str, Any], dependencies=[Depends(SystemPermissionCheck.require('dashboard:read'))])
async def get_user_distribution(
    current_user: Dict[str, Any] = Depends(SystemPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db)
):
    """Get user distribution by role"""
    try:
        service = SystemDashboardService(db)
        distribution = await service.get_user_distribution()
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


@router.get("/top-onboarders", response_model=Dict[str, Any], dependencies=[Depends(SystemPermissionCheck.require('dashboard:read'))])
async def get_top_onboarders(
    limit: int = 5,
    current_user: Dict[str, Any] = Depends(SystemPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db)
):
    """Get top user onboarders"""
    try:
        service = SystemDashboardService(db)
        onboarders = await service.get_top_onboarders(limit)
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


@router.get("/recent-activity", response_model=Dict[str, Any], dependencies=[Depends(SystemPermissionCheck.require('dashboard:read'))])
async def get_recent_activity(
    limit: int = 20,
    current_user: Dict[str, Any] = Depends(SystemPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db)
):
    """Get recent system activity (last 24 hours)"""
    try:
        service = SystemDashboardService(db)
        activity = await service.get_recent_activity(limit)
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
