from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Dashboard import DashboardService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db

router = APIRouter(prefix="/dashboard", tags=["Application Dashboard"])


def _resolve_persona_id(user: Dict[str, Any], persona_id: Optional[int]) -> Optional[int]:
    """
    Resolve the effective persona_id based on the caller's role.

    - Admin/Owner: sees all personas in their workspace — persona_id stays None
      unless the caller explicitly supplied one.
    - Manager / Operator: always scoped to their own persona_id from the token.
      The query param is ignored to prevent cross-persona data leakage.
    """
    user_role = user.get('role', {}).get('name')

    if user_role and user_role.lower() in ('admin', 'owner'):
        # Admin/Owner may optionally filter by a specific persona; otherwise sees all in workspace
        return persona_id or None

    # Manager / Operator are always scoped to their own persona
    return user.get('persona_id')


@router.get("")
async def get_dashboard(
    workspace_id: int = Query(..., description="Workspace ID"),
    persona_id: Optional[int] = Query(None, description="Persona ID (optional, Admin/Owner only)"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('dashboard:read')),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive dashboard data

    Query Parameters:
    - workspace_id: Workspace ID (required)
    - persona_id: Persona ID for filtering (optional, Admin/Owner only)
    - start_date: Start date for filtering data (ISO format, optional)
    - end_date: End date for filtering data (ISO format, optional)

    Returns comprehensive dashboard data including:
    - Statistics (revenue, orders, tables, items)
    - Analytics (revenue trend, order status, popular items, category performance)
    - Recent activity
    - Table statuses
    """
    service = DashboardService(db)

    try:
        effective_persona_id = _resolve_persona_id(user, persona_id)

        dashboard_data = await service.get_venue_dashboard(
            workspace_id=workspace_id,
            persona_id=effective_persona_id,
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


@router.get("/stats")
async def get_dashboard_stats(
    workspace_id: int = Query(..., description="Workspace ID"),
    persona_id: Optional[int] = Query(None, description="Persona ID (optional, Admin/Owner only)"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('dashboard:read')),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard statistics only (lightweight endpoint)

    Query Parameters:
    - workspace_id: Workspace ID (required)
    - persona_id: Persona ID for filtering (optional, Admin/Owner only)
    - start_date: Start date for filtering data (ISO format, optional)
    - end_date: End date for filtering data (ISO format, optional)
    """
    service = DashboardService(db)

    try:
        effective_persona_id = _resolve_persona_id(user, persona_id)

        stats = await service.get_stats_only(
            workspace_id=workspace_id,
            persona_id=effective_persona_id,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "data": {
                "stats": stats
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard stats: {str(e)}"
        )


@router.get("/analytics")
async def get_dashboard_analytics(
    workspace_id: int = Query(..., description="Workspace ID"),
    persona_id: Optional[int] = Query(None, description="Persona ID (optional, Admin/Owner only)"),
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require('dashboard:read')),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard analytics only

    Query Parameters:
    - workspace_id: Workspace ID (required)
    - persona_id: Persona ID for filtering (optional, Admin/Owner only)
    - start_date: Start date for filtering data (ISO format, optional)
    - end_date: End date for filtering data (ISO format, optional)
    """
    service = DashboardService(db)

    try:
        effective_persona_id = _resolve_persona_id(user, persona_id)

        analytics = await service.get_analytics_only(
            workspace_id=workspace_id,
            persona_id=effective_persona_id,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "data": analytics
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard analytics: {str(e)}"
        )
