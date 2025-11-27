"""
Analytics Models
DTOs for analytics and dashboard data
"""
from pydantic import Field
from typing import List, Dict, Any, Optional

from app.models.base import BaseDTO
from app.models.enums import UserRole


# =============================================================================
# ANALYTICS DTOs
# =============================================================================

class SalesAnalyticsDTO(BaseDTO):
    """Consolidated sales analytics DTO"""
    total_revenue: float
    total_orders: int
    average_order_value: float
    popular_items: List[Dict[str, Any]] = Field(default_factory=list)
    revenue_by_day: List[Dict[str, Any]] = Field(default_factory=list)
    orders_by_status: List[Dict[str, Any]] = Field(default_factory=list)


class VenueAnalyticsDTO(BaseDTO):
    """Venue analytics data DTO"""
    venue_id: str
    venue_name: str
    period: str
    total_orders: int = 0
    total_revenue: float = 0.0
    average_order_value: float = 0.0
    total_customers: int = 0
    new_customers: int = 0
    returning_customers: int = 0
    popular_items: List[Dict[str, Any]] = Field(default_factory=list)
    peak_hours: List[Dict[str, Any]] = Field(default_factory=list)
    table_utilization: float = 0.0
    customer_satisfaction: float = 0.0
    order_status_breakdown: Dict[str, int] = Field(default_factory=dict)


class DashboardStatsDTO(BaseDTO):
    """Dashboard statistics DTO"""
    total_orders_today: int = Field(default=0)
    total_revenue_today: float = Field(default=0.0)
    pending_orders: int = Field(default=0)
    active_customers: int = Field(default=0)
    average_order_value: float = Field(default=0.0)
    popular_items: List[Dict[str, Any]] = Field(default_factory=list)
    recent_orders: List[Dict[str, Any]] = Field(default_factory=list)


class DashboardDataDTO(BaseDTO):
    """Dashboard data DTO based on user role"""
    user_role: UserRole
    workspace_id: str
    venue_id: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)
    recent_orders: List[Dict[str, Any]] = Field(default_factory=list)
    analytics: Dict[str, Any] = Field(default_factory=dict)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    quick_actions: List[Dict[str, Any]] = Field(default_factory=list)


class SuperAdminDashboardDTO(DashboardDataDTO):
    """SuperAdmin dashboard DTO with workspace-wide data"""
    all_venues: List[Dict[str, Any]] = Field(default_factory=list)
    workspace_analytics: Dict[str, Any] = Field(default_factory=dict)
    user_management: Dict[str, Any] = Field(default_factory=dict)


class AdminDashboardDTO(DashboardDataDTO):
    """Admin dashboard DTO with venue-specific data"""
    venue_analytics: Optional[VenueAnalyticsDTO] = None
    staff_performance: Dict[str, Any] = Field(default_factory=dict)
    inventory_alerts: List[Dict[str, Any]] = Field(default_factory=list)


class OperatorDashboardDTO(DashboardDataDTO):
    """Operator dashboard DTO with operational data"""
    active_orders: List[Dict[str, Any]] = Field(default_factory=list)
    table_status: List[Dict[str, Any]] = Field(default_factory=list)
    today_summary: Dict[str, Any] = Field(default_factory=dict)