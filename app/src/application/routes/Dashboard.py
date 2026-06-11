"""
Dashboard router — analytics and reporting endpoints.

All endpoints require authentication and a valid persona_id scoped to the
caller's workspace. persona validation is done once per request via
_resolve_persona — no redundant DB calls.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Dashboard import ApplicationDashboardService
from src.application.services.Persona import PersonaService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, PersonaMismatchError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _require_workspace(current_user: Dict[str, Any]) -> int:
    wid = current_user.get("workspace_id")
    if not wid:
        raise BadRequestError("workspace_id could not be resolved for this user")
    return wid


async def _resolve_persona(persona_id: int, db: AsyncSession) -> None:
    """Validate persona exists and is active. Raises PersonaMismatchError if not."""
    persona = await PersonaService(db).get_by_id(persona_id)
    if not persona:
        raise PersonaMismatchError("Persona not found or access denied")


# ---------------------------------------------------------------------------
# GET /dashboard  — full dashboard (all metrics, fully parallelised)
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def get_full_dashboard(
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return all dashboard metrics in one parallelised call."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    logger.info(
        "dashboard.full.request user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )

    await _resolve_persona(persona_id, db)
    data = await ApplicationDashboardService(db).get_full_dashboard(
        workspace_id=workspace_id, persona_id=persona_id
    )

    logger.info(
        "dashboard.full.response user_id=%s workspace_id=%s persona_id=%s sections=%s",
        user_id, workspace_id, persona_id, list(data.keys()),
    )
    return {"success": True, "message": "Dashboard data retrieved successfully", "data": data}


# ---------------------------------------------------------------------------
# GET /dashboard/stats
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=BaseResponse)
async def get_dashboard_stats(
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return key metrics: today/week/month revenue, tables, customers, items, pending orders."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    logger.info(
        "dashboard.stats.request user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )

    await _resolve_persona(persona_id, db)
    data = await ApplicationDashboardService(db).get_dashboard_stats(
        workspace_id=workspace_id, persona_id=persona_id
    )

    logger.info(
        "dashboard.stats.response user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )
    return {"success": True, "message": "Stats retrieved successfully", "data": data}


# ---------------------------------------------------------------------------
# GET /dashboard/revenue-trend
# ---------------------------------------------------------------------------

@router.get("/revenue-trend", response_model=BaseResponse)
async def get_revenue_trend(
    persona_id: int = Query(..., ge=1),
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return revenue + order count per day for the last N days (line chart)."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    logger.info(
        "dashboard.revenue_trend.request user_id=%s workspace_id=%s persona_id=%s days=%s",
        user_id, workspace_id, persona_id, days,
    )

    await _resolve_persona(persona_id, db)
    data = await ApplicationDashboardService(db).get_revenue_trend(
        workspace_id=workspace_id, persona_id=persona_id, days=days
    )

    logger.info(
        "dashboard.revenue_trend.response user_id=%s workspace_id=%s persona_id=%s days=%s points=%s",
        user_id, workspace_id, persona_id, days, len(data),
    )
    return {"success": True, "message": "Revenue trend retrieved successfully", "data": data}


# ---------------------------------------------------------------------------
# GET /dashboard/orders-by-status
# ---------------------------------------------------------------------------

@router.get("/orders-by-status", response_model=BaseResponse)
async def get_orders_by_status(
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return order counts grouped by status (pie/donut chart)."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    logger.info(
        "dashboard.orders_by_status.request user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )

    await _resolve_persona(persona_id, db)
    data = await ApplicationDashboardService(db).get_orders_by_status(
        workspace_id=workspace_id, persona_id=persona_id
    )

    logger.info(
        "dashboard.orders_by_status.response user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )
    return {"success": True, "message": "Orders by status retrieved successfully", "data": data}


# ---------------------------------------------------------------------------
# GET /dashboard/orders-by-type
# ---------------------------------------------------------------------------

@router.get("/orders-by-type", response_model=BaseResponse)
async def get_orders_by_type(
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return order counts grouped by order type: dine_in, takeaway, delivery."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    logger.info(
        "dashboard.orders_by_type.request user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )

    await _resolve_persona(persona_id, db)
    data = await ApplicationDashboardService(db).get_orders_by_type(
        workspace_id=workspace_id, persona_id=persona_id
    )

    logger.info(
        "dashboard.orders_by_type.response user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )
    return {"success": True, "message": "Orders by type retrieved successfully", "data": data}


# ---------------------------------------------------------------------------
# GET /dashboard/top-items
# ---------------------------------------------------------------------------

@router.get("/top-items", response_model=BaseResponse)
async def get_top_items(
    persona_id: int = Query(..., ge=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return top N selling items by quantity (bar chart)."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    logger.info(
        "dashboard.top_items.request user_id=%s workspace_id=%s persona_id=%s limit=%s",
        user_id, workspace_id, persona_id, limit,
    )

    await _resolve_persona(persona_id, db)
    data = await ApplicationDashboardService(db).get_top_items(
        workspace_id=workspace_id, persona_id=persona_id, limit=limit
    )

    logger.info(
        "dashboard.top_items.response user_id=%s workspace_id=%s persona_id=%s returned=%s",
        user_id, workspace_id, persona_id, len(data),
    )
    return {"success": True, "message": "Top items retrieved successfully", "data": data}


# ---------------------------------------------------------------------------
# GET /dashboard/payment-summary
# ---------------------------------------------------------------------------

@router.get("/payment-summary", response_model=BaseResponse)
async def get_payment_summary(
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return payment breakdown by status and method."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    logger.info(
        "dashboard.payment_summary.request user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )

    await _resolve_persona(persona_id, db)
    data = await ApplicationDashboardService(db).get_payment_summary(
        workspace_id=workspace_id, persona_id=persona_id
    )

    logger.info(
        "dashboard.payment_summary.response user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )
    return {"success": True, "message": "Payment summary retrieved successfully", "data": data}


# ---------------------------------------------------------------------------
# GET /dashboard/hourly-orders
# ---------------------------------------------------------------------------

@router.get("/hourly-orders", response_model=BaseResponse)
async def get_hourly_orders(
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return order counts + revenue grouped by hour for today (bar chart)."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    logger.info(
        "dashboard.hourly_orders.request user_id=%s workspace_id=%s persona_id=%s",
        user_id, workspace_id, persona_id,
    )

    await _resolve_persona(persona_id, db)
    data = await ApplicationDashboardService(db).get_hourly_orders(
        workspace_id=workspace_id, persona_id=persona_id
    )

    logger.info(
        "dashboard.hourly_orders.response user_id=%s workspace_id=%s persona_id=%s hours=%s",
        user_id, workspace_id, persona_id, len(data),
    )
    return {"success": True, "message": "Hourly orders retrieved successfully", "data": data}


# ---------------------------------------------------------------------------
# GET /dashboard/category-revenue  — NEW
# ---------------------------------------------------------------------------

@router.get("/category-revenue", response_model=BaseResponse)
async def get_category_revenue(
    persona_id: int = Query(..., ge=1),
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return revenue + quantity per category for the last N days (pie/bar chart)."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    logger.info(
        "dashboard.category_revenue.request user_id=%s workspace_id=%s persona_id=%s days=%s",
        user_id, workspace_id, persona_id, days,
    )

    await _resolve_persona(persona_id, db)
    data = await ApplicationDashboardService(db).get_category_revenue(
        workspace_id=workspace_id, persona_id=persona_id, days=days
    )

    logger.info(
        "dashboard.category_revenue.response user_id=%s workspace_id=%s persona_id=%s categories=%s",
        user_id, workspace_id, persona_id, len(data),
    )
    return {"success": True, "message": "Category revenue retrieved successfully", "data": data}


# ---------------------------------------------------------------------------
# GET /dashboard/table-utilisation  — NEW
# ---------------------------------------------------------------------------

@router.get("/table-utilisation", response_model=BaseResponse)
async def get_table_utilisation(
    persona_id: int = Query(..., ge=1),
    days: int = Query(7, ge=1, le=90),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return order count + revenue per table for the last N days (heatmap/bar)."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    logger.info(
        "dashboard.table_utilisation.request user_id=%s workspace_id=%s persona_id=%s days=%s",
        user_id, workspace_id, persona_id, days,
    )

    await _resolve_persona(persona_id, db)
    data = await ApplicationDashboardService(db).get_table_utilisation(
        workspace_id=workspace_id, persona_id=persona_id, days=days
    )

    logger.info(
        "dashboard.table_utilisation.response user_id=%s workspace_id=%s persona_id=%s tables=%s",
        user_id, workspace_id, persona_id, len(data),
    )
    return {"success": True, "message": "Table utilisation retrieved successfully", "data": data}


# ---------------------------------------------------------------------------
# GET /dashboard/recent-orders  — NEW
# ---------------------------------------------------------------------------

@router.get("/recent-orders", response_model=BaseResponse)
async def get_recent_orders(
    persona_id: int = Query(..., ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return the most recent N orders — live feed / activity widget."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    logger.info(
        "dashboard.recent_orders.request user_id=%s workspace_id=%s persona_id=%s limit=%s",
        user_id, workspace_id, persona_id, limit,
    )

    await _resolve_persona(persona_id, db)
    data = await ApplicationDashboardService(db).get_recent_orders(
        workspace_id=workspace_id, persona_id=persona_id, limit=limit
    )

    logger.info(
        "dashboard.recent_orders.response user_id=%s workspace_id=%s persona_id=%s returned=%s",
        user_id, workspace_id, persona_id, len(data),
    )
    return {"success": True, "message": "Recent orders retrieved successfully", "data": data}


# ---------------------------------------------------------------------------
# GET /dashboard/customer-stats  — NEW
# ---------------------------------------------------------------------------

@router.get("/customer-stats", response_model=BaseResponse)
async def get_customer_stats(
    persona_id: int = Query(..., ge=1),
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return new vs returning customers + top 10 customers by spend."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)
    logger.info(
        "dashboard.customer_stats.request user_id=%s workspace_id=%s persona_id=%s days=%s",
        user_id, workspace_id, persona_id, days,
    )

    await _resolve_persona(persona_id, db)
    data = await ApplicationDashboardService(db).get_customer_stats(
        workspace_id=workspace_id, persona_id=persona_id, days=days
    )

    logger.info(
        "dashboard.customer_stats.response user_id=%s workspace_id=%s persona_id=%s "
        "new=%s returning=%s top_customers=%s",
        user_id, workspace_id, persona_id,
        data.get("new_customers"), data.get("returning_customers"),
        len(data.get("top_customers", [])),
    )
    return {"success": True, "message": "Customer stats retrieved successfully", "data": data}
