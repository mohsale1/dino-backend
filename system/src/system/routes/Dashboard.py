from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.Dashboard import SystemDashboardService

router = APIRouter(prefix="/dashboard", tags=["System Dashboard"])


@router.get(
    "",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("dashboard:view"))],
)
async def get_full_dashboard(db: AsyncSession = Depends(get_db)):
    """Get full dashboard data."""
    service = SystemDashboardService(db)
    stats = await service.get_system_stats()
    billing = await service.get_billing_overview()
    recent = await service.get_recent_activity(limit=10)
    return {
        "success": True,
        "message": "Dashboard data retrieved successfully",
        "data": {
            "stats": stats,
            "billing_overview": billing,
            "recent_activity": recent,
        },
    }


@router.get(
    "/stats",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("dashboard:view"))],
)
async def get_system_stats(db: AsyncSession = Depends(get_db)):
    """Get system statistics."""
    service = SystemDashboardService(db)
    stats = await service.get_system_stats()
    return {"success": True, "message": "Stats retrieved successfully", "data": stats}


@router.get(
    "/workspace-growth",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("dashboard:view"))],
)
async def get_workspace_growth(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get workspace growth trend."""
    service = SystemDashboardService(db)
    data = await service.get_workspace_growth(days=days)
    return {"success": True, "message": "Workspace growth retrieved successfully", "data": data}


@router.get(
    "/user-distribution",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("dashboard:view"))],
)
async def get_user_distribution(db: AsyncSession = Depends(get_db)):
    """Get users grouped by role."""
    service = SystemDashboardService(db)
    data = await service.get_user_distribution()
    return {"success": True, "message": "User distribution retrieved successfully", "data": data}


@router.get(
    "/billing-overview",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("dashboard:view"))],
)
async def get_billing_overview(db: AsyncSession = Depends(get_db)):
    """Get billing summary."""
    service = SystemDashboardService(db)
    data = await service.get_billing_overview()
    return {"success": True, "message": "Billing overview retrieved successfully", "data": data}


@router.get(
    "/recent-activity",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("dashboard:view"))],
)
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get recent system activity."""
    service = SystemDashboardService(db)
    data = await service.get_recent_activity(limit=limit)
    return {"success": True, "message": "Recent activity retrieved successfully", "data": data}


@router.get(
    "/top-workspaces",
    response_model=BaseResponse,
    dependencies=[Depends(SystemPermissionCheck.require("dashboard:view"))],
)
async def get_top_workspaces(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get top workspaces by personas and users."""
    service = SystemDashboardService(db)
    data = await service.get_top_workspaces(limit=limit)
    return {"success": True, "message": "Top workspaces retrieved successfully", "data": data}
