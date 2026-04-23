"""
Dashboard router — analytics and reporting endpoints.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Dashboard import ApplicationDashboardService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _resolve_workspace(current_user: Dict[str, Any], workspace_id: Optional[int]) -> int:
    wid = workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id is required",
        )
    return wid


@router.get("", response_model=BaseResponse)
async def get_full_dashboard(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("dashboard:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get full dashboard summary (all metrics combined)."""
    wid = _resolve_workspace(current_user, workspace_id)
    service = ApplicationDashboardService(db)
    data = await service.get_full_dashboard(workspace_id=wid, persona_id=persona_id)
    return {"success": True, "message": "Dashboard data retrieved successfully", "data": data}


@router.get("/stats", response_model=BaseResponse)
async def get_dashboard_stats(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("dashboard:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get key dashboard metrics (orders, revenue, tables, customers, items)."""
    wid = _resolve_workspace(current_user, workspace_id)
    service = ApplicationDashboardService(db)
    data = await service.get_dashboard_stats(workspace_id=wid, persona_id=persona_id)
    return {"success": True, "message": "Stats retrieved successfully", "data": data}


@router.get("/revenue-trend", response_model=BaseResponse)
async def get_revenue_trend(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("dashboard:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get revenue per day for the last N days."""
    wid = _resolve_workspace(current_user, workspace_id)
    service = ApplicationDashboardService(db)
    data = await service.get_revenue_trend(workspace_id=wid, persona_id=persona_id, days=days)
    return {"success": True, "message": "Revenue trend retrieved successfully", "data": data}


@router.get("/orders-by-status", response_model=BaseResponse)
async def get_orders_by_status(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("dashboard:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get order counts grouped by status (for pie chart)."""
    wid = _resolve_workspace(current_user, workspace_id)
    service = ApplicationDashboardService(db)
    data = await service.get_orders_by_status(workspace_id=wid, persona_id=persona_id)
    return {"success": True, "message": "Orders by status retrieved successfully", "data": data}


@router.get("/orders-by-type", response_model=BaseResponse)
async def get_orders_by_type(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("dashboard:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get order counts grouped by order type (for bar chart)."""
    wid = _resolve_workspace(current_user, workspace_id)
    service = ApplicationDashboardService(db)
    data = await service.get_orders_by_type(workspace_id=wid, persona_id=persona_id)
    return {"success": True, "message": "Orders by type retrieved successfully", "data": data}


@router.get("/top-items", response_model=BaseResponse)
async def get_top_items(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("dashboard:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get top selling items by quantity."""
    wid = _resolve_workspace(current_user, workspace_id)
    service = ApplicationDashboardService(db)
    data = await service.get_top_items(workspace_id=wid, persona_id=persona_id, limit=limit)
    return {"success": True, "message": "Top items retrieved successfully", "data": data}


@router.get("/payment-summary", response_model=BaseResponse)
async def get_payment_summary(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("dashboard:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get payment breakdown by status and method."""
    wid = _resolve_workspace(current_user, workspace_id)
    service = ApplicationDashboardService(db)
    data = await service.get_payment_summary(workspace_id=wid, persona_id=persona_id)
    return {"success": True, "message": "Payment summary retrieved successfully", "data": data}


@router.get("/hourly-orders", response_model=BaseResponse)
async def get_hourly_orders(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("dashboard:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get order counts grouped by hour of day for today."""
    wid = _resolve_workspace(current_user, workspace_id)
    service = ApplicationDashboardService(db)
    data = await service.get_hourly_orders(workspace_id=wid, persona_id=persona_id)
    return {"success": True, "message": "Hourly orders retrieved successfully", "data": data}
