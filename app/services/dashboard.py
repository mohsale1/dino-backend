"""
Dashboard Service
Centralized service for dashboard data aggregation, analytics, and insights
Provides comprehensive metrics for SuperAdmin and Admin users
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from app.core.logging import get_logger
from app.models.entities import OrderStatus, TableStatus, PaymentStatus

logger = get_logger(__name__)


class DashboardService:
    """Service for dashboard data aggregation and analytics"""
    
    def __init__(self):
        self.repo_manager = None
    
    def _get_repo_manager(self):
        """Lazy initialization to avoid circular imports"""
        if self.repo_manager is None:
            from app.core.dependencies import get_repository_manager
            self.repo_manager = get_repository_manager()
        return self.repo_manager
    
    # =========================================================================
    # CORE DASHBOARD METHODS
    # =========================================================================
    
    async def get_superadmin_dashboard(self) -> Dict[str, Any]:
        """
        Get system-wide dashboard for SuperAdmin
        
        Returns:
            - System statistics (workspaces, venues, users, orders)
            - Workspace breakdown
            - Top performing venues
            - System health metrics
        """
        try:
            workspace_repo = self._get_repo_manager().get_repository('workspace')
            venue_repo = self._get_repo_manager().get_repository('venue')
            user_repo = self._get_repo_manager().get_repository('user')
            order_repo = self._get_repo_manager().get_repository('order')
            
            # Get all data
            workspaces = await workspace_repo.get_all()
            venues = await venue_repo.get_all()
            users = await user_repo.get_all()
            orders = await order_repo.get_all()
            
            # Calculate metrics
            active_venues = [v for v in venues if v.get('is_active', False)]
            active_users = [u for u in users if u.get('is_active', False)]
            
            # Revenue calculation
            paid_orders = [o for o in orders if o.get('payment_status') == PaymentStatus.PAID.value]
            total_revenue = sum(o.get('total_amount', 0) for o in paid_orders)
            
            # Today's metrics
            today = datetime.now(timezone.utc).date()
            today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
            today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            today_orders = [
                o for o in orders
                if o.get('created_at') and today_start <= self._ensure_tz(o['created_at']) <= today_end
            ]
            today_revenue = sum(
                o.get('total_amount', 0) for o in today_orders
                if o.get('payment_status') == PaymentStatus.PAID.value
            )
            
            # Workspace breakdown
            workspace_details = []
            for workspace in workspaces:
                ws_id = workspace['id']
                ws_venues = [v for v in venues if v.get('workspace_id') == ws_id]
                ws_users = [u for u in users if u.get('workspace_id') == ws_id]
                
                workspace_details.append({
                    "id": ws_id,
                    "name": workspace.get('name', 'Unknown'),
                    "description": workspace.get('description', ''),
                    "venue_count": len(ws_venues),
                    "user_count": len(ws_users),
                    "is_active": workspace.get('is_active', False),
                    "created_at": self._format_datetime(workspace.get('created_at'))
                })
            
            # Top venues by revenue
            venue_revenue = {}
            for order in paid_orders:
                venue_id = order.get('venue_id')
                if venue_id:
                    venue_revenue[venue_id] = venue_revenue.get(venue_id, 0) + order.get('total_amount', 0)
            
            top_venues = []
            for venue_id, revenue in sorted(venue_revenue.items(), key=lambda x: x[1], reverse=True)[:5]:
                venue = next((v for v in venues if v['id'] == venue_id), None)
                if venue:
                    top_venues.append({
                        "id": venue_id,
                        "name": venue.get('name', 'Unknown'),
                        "revenue": revenue,
                        "order_count": len([o for o in paid_orders if o.get('venue_id') == venue_id])
                    })
            
            return {
                "summary": {
                    "total_workspaces": len(workspaces),
                    "total_venues": len(venues),
                    "active_venues": len(active_venues),
                    "total_users": len(users),
                    "active_users": len(active_users),
                    "total_orders": len(orders),
                    "total_revenue": round(total_revenue, 2),
                    "today_orders": len(today_orders),
                    "today_revenue": round(today_revenue, 2)
                },
                "workspaces": workspace_details,
                "top_venues": top_venues,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting superadmin dashboard: {e}", exc_info=True)
            raise
    
    async def get_venue_dashboard(self, venue_id: str) -> Dict[str, Any]:
        """
        Get comprehensive dashboard for a specific venue
        
        Returns:
            - Venue information
            - Today's summary (orders, revenue, tables)
            - Recent orders
            - Quick stats
        """
        try:
            venue_repo = self._get_repo_manager().get_repository('venue')
            order_repo = self._get_repo_manager().get_repository('order')
            table_repo = self._get_repo_manager().get_repository('table')
            menu_item_repo = self._get_repo_manager().get_repository('menu_item')
            user_repo = self._get_repo_manager().get_repository('user')
            
            # Get venue
            venue = await venue_repo.get_by_id(venue_id)
            if not venue:
                raise ValueError(f"Venue {venue_id} not found")
            
            # Get today's date range
            today = datetime.now(timezone.utc).date()
            today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
            today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            # Get orders
            all_orders = await order_repo.get_by_venue(venue_id)
            today_orders = [
                o for o in all_orders
                if o.get('created_at') and today_start <= self._ensure_tz(o['created_at']) <= today_end
            ]
            
            # Calculate revenue
            today_revenue = sum(
                o.get('total_amount', 0) for o in today_orders
                if o.get('payment_status') == PaymentStatus.PAID.value
            )
            
            total_revenue = sum(
                o.get('total_amount', 0) for o in all_orders
                if o.get('payment_status') == PaymentStatus.PAID.value
            )
            
            # Get tables
            tables = await table_repo.get_by_venue(venue_id)
            active_tables = [t for t in tables if t.get('is_active', False)]
            occupied_tables = [
                t for t in active_tables
                if t.get('table_status') == TableStatus.OCCUPIED.value
            ]
            
            # Get menu items
            menu_items = await menu_item_repo.get_by_venue(venue_id)
            active_menu_items = [m for m in menu_items if m.get('is_available', False)]
            
            # Get staff
            staff = await user_repo.get_by_venue(venue_id)
            active_staff = [s for s in staff if s.get('is_active', False)]
            
            # Recent orders (last 10)
            recent_orders = sorted(
                all_orders,
                key=lambda x: self._ensure_tz(x.get('created_at', datetime.min)),
                reverse=True
            )[:10]
            
            formatted_recent_orders = []
            for order in recent_orders:
                # Get table info
                table_number = None
                if order.get('table_id'):
                    table = await table_repo.get_by_id(order['table_id'])
                    if table:
                        table_number = table.get('table_number')
                
                formatted_recent_orders.append({
                    "id": order['id'],
                    "order_number": order.get('order_number', 'N/A'),
                    "table_number": table_number,
                    "items_count": len(order.get('items', [])),
                    "total_amount": round(order.get('total_amount', 0), 2),
                    "status": order.get('status', 'unknown'),
                    "payment_status": order.get('payment_status', 'unknown'),
                    "created_at": self._format_datetime(order.get('created_at')),
                    "time_ago": self._calculate_time_ago(order.get('created_at'))
                })
            
            # Active orders
            active_statuses = [
                OrderStatus.PENDING.value,
                OrderStatus.CONFIRMED.value,
                OrderStatus.PREPARING.value,
                OrderStatus.READY.value
            ]
            active_orders = [o for o in all_orders if o.get('status') in active_statuses]
            
            # Order status breakdown
            status_breakdown = {}
            for status in OrderStatus:
                count = len([o for o in all_orders if o.get('status') == status.value])
                if count > 0:
                    status_breakdown[status.value] = {
                        "count": count,
                        "percentage": round((count / len(all_orders) * 100), 1) if all_orders else 0
                    }
            
            # Revenue trend (last 7 days)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=6)
            revenue_trend = await self._calculate_revenue_trend(all_orders, start_date, end_date)
            
            # Popular menu items
            popular_items = await self._get_popular_items(venue_id, all_orders, limit=10)
            
            # Peak hours
            peak_hours = self._calculate_peak_hours(all_orders)
            
            # Payment method breakdown
            payment_breakdown = {}
            for order in all_orders:
                method = order.get('payment_method', 'unknown')
                status = order.get('payment_status', 'unknown')
                if method not in payment_breakdown:
                    payment_breakdown[method] = {"count": 0, "revenue": 0, "paid": 0, "pending": 0}
                payment_breakdown[method]["count"] += 1
                if status == PaymentStatus.PAID.value:
                    payment_breakdown[method]["paid"] += 1
                    payment_breakdown[method]["revenue"] += order.get('total_amount', 0)
                else:
                    payment_breakdown[method]["pending"] += 1
            
            formatted_payment_breakdown = [
                {
                    "method": method,
                    "count": data["count"],
                    "revenue": round(data["revenue"], 2),
                    "paid": data["paid"],
                    "pending": data["pending"]
                }
                for method, data in payment_breakdown.items()
            ]
            
            # Category performance
            category_performance = await self._calculate_category_performance(venue_id, all_orders)
            
            # Table status breakdown
            table_status_breakdown = {
                "available": len([t for t in active_tables if t.get('table_status') == TableStatus.AVAILABLE.value]),
                "occupied": len(occupied_tables),
                "reserved": len([t for t in active_tables if t.get('table_status') == TableStatus.RESERVED.value]),
                "maintenance": len([t for t in active_tables if t.get('table_status') == TableStatus.MAINTENANCE.value])
            }
            
            return {
                "venue": {
                    "id": venue['id'],
                    "name": venue.get('name', 'Unknown'),
                    "description": venue.get('description', ''),
                    "is_active": venue.get('is_active', False),
                    "is_open": venue.get('is_open', False),
                    "status": venue.get('status', 'unknown')
                },
                "summary": {
                    "today_orders": len(today_orders),
                    "today_revenue": round(today_revenue, 2),
                    "total_orders": len(all_orders),
                    "total_revenue": round(total_revenue, 2),
                    "active_orders": len(active_orders),
                    "total_tables": len(active_tables),
                    "occupied_tables": len(occupied_tables),
                    "table_occupancy_rate": round((len(occupied_tables) / len(active_tables) * 100), 1) if active_tables else 0,
                    "total_menu_items": len(menu_items),
                    "active_menu_items": len(active_menu_items),
                    "total_staff": len(staff),
                    "active_staff": len(active_staff),
                    "average_order_value": round(today_revenue / len(today_orders), 2) if today_orders else 0
                },
                "recent_orders": formatted_recent_orders,
                "analytics": {
                    "order_status_breakdown": status_breakdown,
                    "revenue_trend": revenue_trend,
                    "popular_items": popular_items,
                    "peak_hours": peak_hours,
                    "payment_methods": formatted_payment_breakdown,
                    "category_performance": category_performance,
                    "table_status_breakdown": table_status_breakdown
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting venue dashboard: {e}", exc_info=True)
            raise
    
    # =========================================================================
    # ANALYTICS METHODS
    # =========================================================================
    
    async def get_analytics(
        self,
        venue_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get comprehensive analytics for venue"""
        try:
            order_repo = self._get_repo_manager().get_repository('order')
            
            # Get orders in date range
            all_orders = await order_repo.get_by_venue(venue_id)
            period_orders = [
                o for o in all_orders
                if o.get('created_at') and start_date <= self._ensure_tz(o['created_at']) <= end_date
            ]
            
            # Calculate metrics
            paid_orders = [o for o in period_orders if o.get('payment_status') == PaymentStatus.PAID.value]
            total_revenue = sum(o.get('total_amount', 0) for o in paid_orders)
            total_orders = len(period_orders)
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
            
            # Order status breakdown
            status_breakdown = {}
            for status in OrderStatus:
                count = len([o for o in period_orders if o.get('status') == status.value])
                if count > 0:
                    status_breakdown[status.value] = {
                        "count": count,
                        "percentage": round((count / total_orders * 100), 1) if total_orders > 0 else 0
                    }
            
            # Revenue trend
            revenue_trend = await self._calculate_revenue_trend(period_orders, start_date, end_date)
            
            # Popular items
            popular_items = await self._get_popular_items(venue_id, period_orders, limit=10)
            
            # Peak hours
            peak_hours = self._calculate_peak_hours(period_orders)
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": (end_date - start_date).days + 1
                },
                "summary": {
                    "total_revenue": round(total_revenue, 2),
                    "total_orders": total_orders,
                    "average_order_value": round(avg_order_value, 2),
                    "paid_orders": len(paid_orders),
                    "pending_payment": len(period_orders) - len(paid_orders)
                },
                "order_status_breakdown": status_breakdown,
                "revenue_trend": revenue_trend,
                "popular_items": popular_items,
                "peak_hours": peak_hours,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics: {e}", exc_info=True)
            raise
    
    async def get_revenue_analytics(
        self,
        venue_id: str,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "day"
    ) -> Dict[str, Any]:
        """Get detailed revenue analytics"""
        try:
            order_repo = self._get_repo_manager().get_repository('order')
            
            # Get orders
            all_orders = await order_repo.get_by_venue(venue_id)
            period_orders = [
                o for o in all_orders
                if o.get('created_at') and start_date <= self._ensure_tz(o['created_at']) <= end_date
            ]
            
            paid_orders = [o for o in period_orders if o.get('payment_status') == PaymentStatus.PAID.value]
            
            # Revenue trend
            revenue_trend = await self._calculate_revenue_trend(paid_orders, start_date, end_date, granularity)
            
            # Payment method breakdown
            payment_breakdown = {}
            for order in paid_orders:
                method = order.get('payment_method', 'unknown')
                if method not in payment_breakdown:
                    payment_breakdown[method] = {"count": 0, "revenue": 0}
                payment_breakdown[method]["count"] += 1
                payment_breakdown[method]["revenue"] += order.get('total_amount', 0)
            
            # Format payment breakdown
            formatted_payment_breakdown = [
                {
                    "method": method,
                    "count": data["count"],
                    "revenue": round(data["revenue"], 2),
                    "percentage": round((data["revenue"] / sum(d["revenue"] for d in payment_breakdown.values()) * 100), 1)
                }
                for method, data in payment_breakdown.items()
            ]
            
            # Calculate growth
            total_revenue = sum(o.get('total_amount', 0) for o in paid_orders)
            days = (end_date - start_date).days + 1
            avg_daily_revenue = total_revenue / days if days > 0 else 0
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "granularity": granularity
                },
                "summary": {
                    "total_revenue": round(total_revenue, 2),
                    "average_daily_revenue": round(avg_daily_revenue, 2),
                    "total_transactions": len(paid_orders),
                    "average_transaction_value": round(total_revenue / len(paid_orders), 2) if paid_orders else 0
                },
                "revenue_trend": revenue_trend,
                "payment_methods": formatted_payment_breakdown,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue analytics: {e}", exc_info=True)
            raise
    
    async def get_order_analytics(
        self,
        venue_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get detailed order analytics"""
        try:
            order_repo = self._get_repo_manager().get_repository('order')
            
            # Get orders
            all_orders = await order_repo.get_by_venue(venue_id)
            period_orders = [
                o for o in all_orders
                if o.get('created_at') and start_date <= self._ensure_tz(o['created_at']) <= end_date
            ]
            
            # Status breakdown
            status_breakdown = {}
            for status in OrderStatus:
                count = len([o for o in period_orders if o.get('status') == status.value])
                status_breakdown[status.value] = count
            
            # Peak hours
            peak_hours = self._calculate_peak_hours(period_orders)
            
            # Order volume trend
            order_trend = self._calculate_order_trend(period_orders, start_date, end_date)
            
            # Average preparation time (simplified)
            completed_orders = [o for o in period_orders if o.get('status') == OrderStatus.DELIVERED.value]
            avg_prep_time = 20  # Placeholder - would need actual tracking
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "summary": {
                    "total_orders": len(period_orders),
                    "completed_orders": len(completed_orders),
                    "completion_rate": round((len(completed_orders) / len(period_orders) * 100), 1) if period_orders else 0,
                    "average_prep_time_minutes": avg_prep_time
                },
                "status_breakdown": status_breakdown,
                "order_trend": order_trend,
                "peak_hours": peak_hours,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting order analytics: {e}", exc_info=True)
            raise
    
    async def get_menu_analytics(
        self,
        venue_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get menu performance analytics"""
        try:
            order_repo = self._get_repo_manager().get_repository('order')
            menu_item_repo = self._get_repo_manager().get_repository('menu_item')
            
            # Get orders
            all_orders = await order_repo.get_by_venue(venue_id)
            period_orders = [
                o for o in all_orders
                if o.get('created_at') and start_date <= self._ensure_tz(o['created_at']) <= end_date
            ]
            
            # Get popular items
            popular_items = await self._get_popular_items(venue_id, period_orders, limit)
            
            # Category performance
            category_performance = await self._calculate_category_performance(venue_id, period_orders)
            
            # Get all menu items for availability rate
            all_menu_items = await menu_item_repo.get_by_venue(venue_id)
            available_items = [m for m in all_menu_items if m.get('is_available', False)]
            
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "summary": {
                    "total_menu_items": len(all_menu_items),
                    "available_items": len(available_items),
                    "availability_rate": round((len(available_items) / len(all_menu_items) * 100), 1) if all_menu_items else 0
                },
                "top_items": popular_items,
                "category_performance": category_performance,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting menu analytics: {e}", exc_info=True)
            raise
    
    async def get_live_metrics(self, venue_id: str) -> Dict[str, Any]:
        """Get real-time metrics for venue"""
        try:
            order_repo = self._get_repo_manager().get_repository('order')
            table_repo = self._get_repo_manager().get_repository('table')
            
            # Get today's orders
            today = datetime.now(timezone.utc).date()
            today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
            today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            all_orders = await order_repo.get_by_venue(venue_id)
            today_orders = [
                o for o in all_orders
                if o.get('created_at') and today_start <= self._ensure_tz(o['created_at']) <= today_end
            ]
            
            # Active orders
            active_statuses = [
                OrderStatus.PENDING.value,
                OrderStatus.CONFIRMED.value,
                OrderStatus.PREPARING.value,
                OrderStatus.READY.value
            ]
            active_orders = [o for o in all_orders if o.get('status') in active_statuses]
            
            # Today's revenue
            today_revenue = sum(
                o.get('total_amount', 0) for o in today_orders
                if o.get('payment_status') == PaymentStatus.PAID.value
            )
            
            # Table status
            tables = await table_repo.get_by_venue(venue_id)
            active_tables = [t for t in tables if t.get('is_active', False)]
            occupied_tables = [
                t for t in active_tables
                if t.get('table_status') == TableStatus.OCCUPIED.value
            ]
            
            # Order breakdown
            pending = len([o for o in active_orders if o.get('status') == OrderStatus.PENDING.value])
            preparing = len([o for o in active_orders if o.get('status') == OrderStatus.PREPARING.value])
            ready = len([o for o in active_orders if o.get('status') == OrderStatus.READY.value])
            
            return {
                "venue_id": venue_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "today": {
                    "orders": len(today_orders),
                    "revenue": round(today_revenue, 2),
                    "average_order_value": round(today_revenue / len(today_orders), 2) if today_orders else 0
                },
                "active_orders": {
                    "total": len(active_orders),
                    "pending": pending,
                    "preparing": preparing,
                    "ready": ready
                },
                "tables": {
                    "total": len(active_tables),
                    "occupied": len(occupied_tables),
                    "available": len(active_tables) - len(occupied_tables),
                    "occupancy_rate": round((len(occupied_tables) / len(active_tables) * 100), 1) if active_tables else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting live metrics: {e}", exc_info=True)
            raise
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _calculate_revenue_trend(
        self,
        orders: List[Dict],
        start_date: datetime,
        end_date: datetime,
        granularity: str = "day"
    ) -> List[Dict[str, Any]]:
        """Calculate revenue trend over time"""
        try:
            trend_data = {}
            
            # Initialize periods
            current = start_date
            while current <= end_date:
                if granularity == "day":
                    key = current.strftime("%Y-%m-%d")
                    current += timedelta(days=1)
                elif granularity == "week":
                    key = current.strftime("%Y-W%W")
                    current += timedelta(weeks=1)
                else:  # month
                    key = current.strftime("%Y-%m")
                    if current.month == 12:
                        current = current.replace(year=current.year + 1, month=1)
                    else:
                        current = current.replace(month=current.month + 1)
                
                trend_data[key] = {"revenue": 0, "orders": 0}
            
            # Aggregate orders
            for order in orders:
                if not order.get('created_at'):
                    continue
                
                order_date = self._ensure_tz(order['created_at'])
                
                if granularity == "day":
                    key = order_date.strftime("%Y-%m-%d")
                elif granularity == "week":
                    key = order_date.strftime("%Y-W%W")
                else:  # month
                    key = order_date.strftime("%Y-%m")
                
                if key in trend_data:
                    trend_data[key]["orders"] += 1
                    if order.get('payment_status') == PaymentStatus.PAID.value:
                        trend_data[key]["revenue"] += order.get('total_amount', 0)
            
            # Format output
            return [
                {
                    "period": period,
                    "revenue": round(data["revenue"], 2),
                    "orders": data["orders"],
                    "average_order_value": round(data["revenue"] / data["orders"], 2) if data["orders"] > 0 else 0
                }
                for period, data in sorted(trend_data.items())
            ]
            
        except Exception as e:
            logger.error(f"Error calculating revenue trend: {e}")
            return []
    
    def _calculate_order_trend(
        self,
        orders: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Calculate order volume trend"""
        try:
            trend_data = {}
            
            # Initialize days
            current = start_date
            while current <= end_date:
                key = current.strftime("%Y-%m-%d")
                trend_data[key] = 0
                current += timedelta(days=1)
            
            # Count orders per day
            for order in orders:
                if not order.get('created_at'):
                    continue
                
                order_date = self._ensure_tz(order['created_at'])
                key = order_date.strftime("%Y-%m-%d")
                
                if key in trend_data:
                    trend_data[key] += 1
            
            return [
                {"date": date, "orders": count}
                for date, count in sorted(trend_data.items())
            ]
            
        except Exception as e:
            logger.error(f"Error calculating order trend: {e}")
            return []
    
    def _calculate_peak_hours(self, orders: List[Dict]) -> List[Dict[str, Any]]:
        """Calculate peak hours from orders"""
        try:
            hourly_data = {hour: 0 for hour in range(24)}
            
            for order in orders:
                if not order.get('created_at'):
                    continue
                
                hour = self._ensure_tz(order['created_at']).hour
                hourly_data[hour] += 1
            
            max_orders = max(hourly_data.values()) if hourly_data else 0
            
            return [
                {
                    "hour": f"{hour:02d}:00",
                    "orders": count,
                    "is_peak": count >= (max_orders * 0.7) if max_orders > 0 else False
                }
                for hour, count in sorted(hourly_data.items())
                if count > 0
            ]
            
        except Exception as e:
            logger.error(f"Error calculating peak hours: {e}")
            return []
    
    async def _get_popular_items(
        self,
        venue_id: str,
        orders: List[Dict],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get popular menu items from orders"""
        try:
            menu_item_repo = self._get_repo_manager().get_repository('menu_item')
            
            # Count items
            item_stats = {}
            for order in orders:
                for item in order.get('items', []):
                    item_id = item.get('menu_item_id')
                    if not item_id:
                        continue
                    
                    if item_id not in item_stats:
                        item_stats[item_id] = {"quantity": 0, "revenue": 0}
                    
                    quantity = item.get('quantity', 1)
                    price = item.get('price', 0)
                    
                    item_stats[item_id]["quantity"] += quantity
                    item_stats[item_id]["revenue"] += (price * quantity)
            
            # Get menu item details
            popular_items = []
            total_revenue = sum(stats["revenue"] for stats in item_stats.values())
            
            for item_id, stats in sorted(item_stats.items(), key=lambda x: x[1]["quantity"], reverse=True)[:limit]:
                try:
                    menu_item = await menu_item_repo.get_by_id(item_id)
                    if menu_item:
                        popular_items.append({
                            "id": item_id,
                            "name": menu_item.get('name', 'Unknown'),
                            "category": menu_item.get('category', 'Unknown'),
                            "orders": stats["quantity"],
                            "revenue": round(stats["revenue"], 2),
                            "revenue_percentage": round((stats["revenue"] / total_revenue * 100), 1) if total_revenue > 0 else 0,
                            "image_url": menu_item.get('image_url')
                        })
                except Exception as e:
                    logger.warning(f"Could not get menu item {item_id}: {e}")
                    continue
            
            return popular_items
            
        except Exception as e:
            logger.error(f"Error getting popular items: {e}")
            return []
    
    async def _calculate_category_performance(
        self,
        venue_id: str,
        orders: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Calculate performance by menu category"""
        try:
            menu_item_repo = self._get_repo_manager().get_repository('menu_item')
            
            # Get all menu items to map categories
            menu_items = await menu_item_repo.get_by_venue(venue_id)
            item_category_map = {item['id']: item.get('category', 'Unknown') for item in menu_items}
            
            # Count by category
            category_stats = {}
            for order in orders:
                for item in order.get('items', []):
                    item_id = item.get('menu_item_id')
                    if not item_id:
                        continue
                    
                    category = item_category_map.get(item_id, 'Unknown')
                    if category not in category_stats:
                        category_stats[category] = {"quantity": 0, "revenue": 0}
                    
                    quantity = item.get('quantity', 1)
                    price = item.get('price', 0)
                    
                    category_stats[category]["quantity"] += quantity
                    category_stats[category]["revenue"] += (price * quantity)
            
            # Format output
            total_revenue = sum(stats["revenue"] for stats in category_stats.values())
            
            return [
                {
                    "category": category,
                    "orders": stats["quantity"],
                    "revenue": round(stats["revenue"], 2),
                    "percentage": round((stats["revenue"] / total_revenue * 100), 1) if total_revenue > 0 else 0
                }
                for category, stats in sorted(category_stats.items(), key=lambda x: x[1]["revenue"], reverse=True)
            ]
            
        except Exception as e:
            logger.error(f"Error calculating category performance: {e}")
            return []
    
    def _ensure_tz(self, dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware"""
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
    def _format_datetime(self, dt: Optional[datetime]) -> str:
        """Format datetime to ISO string"""
        if not dt:
            return datetime.now(timezone.utc).isoformat()
        return self._ensure_tz(dt).isoformat()
    
    def _calculate_time_ago(self, dt: Optional[datetime]) -> str:
        """Calculate human-readable time ago"""
        if not dt:
            return "Unknown"
        
        try:
            now = datetime.now(timezone.utc)
            dt = self._ensure_tz(dt)
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days}d ago"
            elif diff.seconds >= 3600:
                hours = diff.seconds // 3600
                return f"{hours}h ago"
            elif diff.seconds >= 60:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            else:
                return "Just now"
        except Exception:
            return "Unknown"


# Global instance
dashboard_service = DashboardService()