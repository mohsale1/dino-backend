"""
Dashboard Service
Handles complex dashboard data aggregation and analytics
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from fastapi import HTTPException, status

from app.core.logging_config import get_logger
# Import moved to avoid circular dependency
from app.models.schemas import OrderStatus, TableStatus, PaymentStatus

logger = get_logger(__name__)


class DashboardService:
    """Service for dashboard data aggregation and analytics"""
    
    def __init__(self):
        self.repo_manager = None
    
    def _get_repo_manager(self):
        """Lazy initialization of repository manager to avoid circular imports"""
        if self.repo_manager is None:
            from app.core.dependency_injection import get_repository_manager
            self.repo_manager = get_repository_manager()
        return self.repo_manager
    
    async def get_superadmin_dashboard_data(self, current_user: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive dashboard data for super admin"""
        try:
            # Get repositories
            workspace_repo = self._get_repo_manager().get_repository('workspace')
            venue_repo = self._get_repo_manager().get_repository('venue')
            user_repo = self._get_repo_manager().get_repository('user')
            order_repo = self._get_repo_manager().get_repository('order')
            table_repo = self._get_repo_manager().get_repository('table')
            menu_item_repo = self._get_repo_manager().get_repository('menu_item')
            
            # Get today's date range (timezone-aware)
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
            today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            # Get all data
            workspaces = await workspace_repo.get_all()
            venues = await venue_repo.get_all()
            users = await user_repo.get_all()
            orders = await order_repo.get_all()
            tables = await table_repo.get_all()
            menu_items = await menu_item_repo.get_all()
            
            # Filter active entities
            active_venues = [v for v in venues if v.get('is_active', False)]
            active_tables = [t for t in tables if t.get('is_active', False)]
            active_menu_items = [m for m in menu_items if m.get('is_available', False)]
            
            # Calculate today's data
            today_orders = []
            for order in orders:
                created_at = order.get('created_at')
                if created_at:
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    if today_start <= created_at <= today_end:
                        today_orders.append(order)
            
            # Calculate revenue
            paid_orders = [o for o in orders if o.get('payment_status') == PaymentStatus.PAID.value]
            total_revenue = sum(order.get('total_amount', 0) for order in paid_orders)
            
            today_paid_orders = [o for o in today_orders if o.get('payment_status') == PaymentStatus.PAID.value]
            today_revenue = sum(order.get('total_amount', 0) for order in today_paid_orders)
            
            # Calculate active orders
            active_statuses = [
                OrderStatus.PENDING.value,
                OrderStatus.CONFIRMED.value,
                OrderStatus.PREPARING.value,
                OrderStatus.READY.value,
                OrderStatus.OUT_FOR_DELIVERY.value
            ]
            active_orders = [o for o in orders if o.get('status') in active_statuses]
            
            # Calculate table occupancy
            occupied_tables = [t for t in active_tables if t.get('table_status') == TableStatus.OCCUPIED.value]
            table_occupancy_rate = round((len(occupied_tables) / len(active_tables)) * 100, 1) if active_tables else 0
            
            # Calculate average order value
            avg_order_value = round(total_revenue / len(paid_orders), 2) if paid_orders else 0
            
            # Get top performing menu items (by order count)
            menu_item_performance = {}
            for order in orders:
                items = order.get('items', [])
                for item in items:
                    menu_item_id = item.get('menu_item_id')
                    if menu_item_id:
                        if menu_item_id not in menu_item_performance:
                            menu_item_performance[menu_item_id] = {
                                'orders': 0,
                                'revenue': 0,
                                'quantity': 0
                            }
                        menu_item_performance[menu_item_id]['orders'] += 1
                        menu_item_performance[menu_item_id]['revenue'] += item.get('total_price', 0)
                        menu_item_performance[menu_item_id]['quantity'] += item.get('quantity', 1)
            
            # Get top 10 menu items with details
            top_menu_items = []
            sorted_items = sorted(menu_item_performance.items(), key=lambda x: x[1]['orders'], reverse=True)[:10]
            
            for menu_item_id, performance in sorted_items:
                # Find menu item details
                menu_item = next((m for m in menu_items if m['id'] == menu_item_id), None)
                if menu_item:
                    # Find venue name
                    venue = next((v for v in venues if v['id'] == menu_item.get('venue_id')), None)
                    venue_name = venue.get('name', 'Unknown') if venue else 'Unknown'
                    
                    top_menu_items.append({
                        'id': menu_item_id,
                        'name': menu_item.get('name', 'Unknown'),
                        'venue_name': venue_name,
                        'category': menu_item.get('category', 'Unknown'),
                        'orders': performance['orders'],
                        'revenue': performance['revenue'],
                        'quantity_sold': performance['quantity'],
                        'price': menu_item.get('price', 0),
                        'rating': menu_item.get('rating', 0) or 4.0
                    })
            
            # Get recent orders (last 20 across all venues)
            def get_order_date(order):
                created_at = order.get('created_at')
                if created_at is None:
                    return datetime.min.replace(tzinfo=timezone.utc)
                if created_at.tzinfo is None:
                    return created_at.replace(tzinfo=timezone.utc)
                return created_at
            
            recent_orders = sorted(orders, key=get_order_date, reverse=True)[:20]
            
            # Format recent orders with venue and table info
            formatted_recent_orders = []
            for order in recent_orders:
                # Get venue name
                venue = next((v for v in venues if v['id'] == order.get('venue_id')), None)
                venue_name = venue.get('name', 'Unknown') if venue else 'Unknown'
                
                # Get table number if available
                table_number = None
                if order.get('table_id'):
                    table = next((t for t in tables if t['id'] == order['table_id']), None)
                    if table:
                        table_number = table.get('table_number')
                
                formatted_recent_orders.append({
                    'id': order['id'],
                    'order_number': order.get('order_number', 'N/A'),
                    'venue_name': venue_name,
                    'table_number': table_number,
                    'total_amount': order.get('total_amount', 0),
                    'status': order.get('status', 'unknown'),
                    'payment_status': order.get('payment_status', 'unknown'),
                    'created_at': order.get('created_at', datetime.utcnow()).isoformat() if order.get('created_at') else datetime.utcnow().isoformat(),
                })
            
            # Calculate venue performance
            venue_performance = []
            for venue in active_venues:
                venue_id = venue['id']
                venue_orders = [o for o in orders if o.get('venue_id') == venue_id]
                venue_today_orders = [o for o in today_orders if o.get('venue_id') == venue_id]
                venue_paid_orders = [o for o in venue_orders if o.get('payment_status') == PaymentStatus.PAID.value]
                venue_revenue = sum(order.get('total_amount', 0) for order in venue_paid_orders)
                venue_tables = [t for t in active_tables if t.get('venue_id') == venue_id]
                venue_occupied_tables = [t for t in venue_tables if t.get('table_status') == TableStatus.OCCUPIED.value]
                
                venue_performance.append({
                    'id': venue_id,
                    'name': venue.get('name', 'Unknown'),
                    'total_orders': len(venue_orders),
                    'today_orders': len(venue_today_orders),
                    'total_revenue': venue_revenue,
                    'total_tables': len(venue_tables),
                    'occupied_tables': len(venue_occupied_tables),
                    'occupancy_rate': round((len(venue_occupied_tables) / len(venue_tables)) * 100, 1) if venue_tables else 0,
                    'is_open': venue.get('is_open', False),
                    'status': venue.get('status', 'unknown')
                })
            
            # Prepare workspace details with enhanced data
            workspace_details = []
            for workspace in workspaces:
                workspace_id = workspace['id']
                
                # Count entities in this workspace
                workspace_venues = [v for v in venues if v.get('workspace_id') == workspace_id]
                workspace_users = [u for u in users if u.get('workspace_id') == workspace_id]
                workspace_orders = [o for o in orders if any(v['id'] == o.get('venue_id') for v in workspace_venues)]
                workspace_revenue = sum(order.get('total_amount', 0) for order in workspace_orders if order.get('payment_status') == PaymentStatus.PAID.value)
                
                workspace_details.append({
                    "id": workspace_id,
                    "name": workspace.get('name', 'Unknown'),
                    "venue_count": len(workspace_venues),
                    "user_count": len(workspace_users),
                    "total_orders": len(workspace_orders),
                    "total_revenue": workspace_revenue,
                    "is_active": workspace.get('is_active', False),
                    "created_at": workspace.get('created_at', datetime.utcnow()).isoformat() if workspace.get('created_at') else datetime.utcnow().isoformat(),
                })
            
            return {
                "system_stats": {
                    "total_workspaces": len(workspaces),
                    "total_venues": len(venues),
                    "total_active_venues": len(active_venues),
                    "total_users": len(users),
                    "total_orders": len(orders),
                    "total_orders_today": len(today_orders),
                    "total_revenue": total_revenue,
                    "total_revenue_today": today_revenue,
                    "active_orders": len(active_orders),
                    "total_tables": len(active_tables),
                    "occupied_tables": len(occupied_tables),
                    "total_menu_items": len(menu_items),
                    "active_menu_items": len(active_menu_items),
                    "table_occupancy_rate": table_occupancy_rate,
                    "avg_order_value": avg_order_value
                },
                "workspaces": workspace_details,
                "venue_performance": venue_performance,
                "top_menu_items": top_menu_items,
                "recent_activity": formatted_recent_orders,
                "analytics": {
                    "order_status_breakdown": {status.value: len([o for o in orders if o.get('status') == status.value]) for status in OrderStatus},
                    "table_status_breakdown": {status.value: len([t for t in active_tables if t.get('table_status') == status.value]) for status in TableStatus},
                    "revenue_by_venue": {venue['name']: sum(order.get('total_amount', 0) for order in orders if order.get('venue_id') == venue['id'] and order.get('payment_status') == PaymentStatus.PAID.value) for venue in active_venues}
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting superadmin dashboard data: {e}")
            raise
    
    async def get_admin_dashboard_data(self, venue_id: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
        """Get dashboard data for venue admin"""
        try:
            # Get repositories
            order_repo = self._get_repo_manager().get_repository('order')
            table_repo = self._get_repo_manager().get_repository('table')
            menu_item_repo = self._get_repo_manager().get_repository('menu_item')
            user_repo = self._get_repo_manager().get_repository('user')
            
            # Get today's date range (timezone-aware)
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
            today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            # Get all orders for this venue
            all_orders = await order_repo.get_by_venue(venue_id)
            
            # Filter today's orders
            today_orders = []
            for order in all_orders:
                created_at = order.get('created_at')
                if created_at:
                    # Ensure created_at is timezone-aware
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    if today_start <= created_at <= today_end:
                        today_orders.append(order)
            
            # Calculate today's revenue (only paid orders)
            today_revenue = sum(
                order.get('total_amount', 0) 
                for order in today_orders 
                if order.get('payment_status') == PaymentStatus.PAID.value
            )
            
            # Get tables for this venue
            tables = await table_repo.get_by_venue(venue_id)
            active_tables = [t for t in tables if t.get('is_active', False)]
            occupied_tables = [
                t for t in active_tables 
                if t.get('table_status') == TableStatus.OCCUPIED.value
            ]
            
            # Get menu items for this venue
            menu_items = await menu_item_repo.get_by_venue(venue_id)
            active_menu_items = [m for m in menu_items if m.get('is_available', False)]
            
            # Get staff for this venue
            staff = await user_repo.get_by_venue(venue_id)
            
            # Get recent orders (last 10)
            def get_order_date(order):
                created_at = order.get('created_at')
                if created_at is None:
                    return datetime.min.replace(tzinfo=timezone.utc)
                # Ensure timezone-aware
                if created_at.tzinfo is None:
                    return created_at.replace(tzinfo=timezone.utc)
                return created_at
            
            recent_orders = sorted(
                all_orders,
                key=get_order_date,
                reverse=True
            )[:10]
            
            # Format recent orders
            formatted_recent_orders = []
            for order in recent_orders:
                # Get table number if available
                table_number = None
                if order.get('table_id'):
                    table = await table_repo.get_by_id(order['table_id'])
                    if table:
                        table_number = table.get('table_number')
                
                formatted_recent_orders.append({
                    "id": order['id'],
                    "order_number": order.get('order_number', 'N/A'),
                    "table_number": table_number,
                    "total_amount": order.get('total_amount', 0),
                    "status": order.get('status', 'unknown'),
                    "created_at": order.get('created_at', datetime.utcnow()).isoformat() if order.get('created_at') else datetime.utcnow().isoformat(),
                })
            
            return {
                "summary": {
                    "today_orders": len(today_orders),
                    "today_revenue": today_revenue,
                    "total_tables": len(active_tables),
                    "occupied_tables": len(occupied_tables),
                    "total_menu_items": len(menu_items),
                    "active_menu_items": len(active_menu_items),
                    "total_staff": len(staff),
                },
                "recent_orders": formatted_recent_orders,
            }
            
        except Exception as e:
            logger.error(f"Error getting admin dashboard data: {e}")
            raise
    
    async def get_operator_dashboard_data(self, venue_id: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
        """Get dashboard data for venue operator"""
        try:
            # Get repositories
            order_repo = self._get_repo_manager().get_repository('order')
            table_repo = self._get_repo_manager().get_repository('table')
            
            # Get all orders for this venue
            all_orders = await order_repo.get_by_venue(venue_id)
            
            # Filter active orders (not completed/cancelled)
            active_statuses = [
                OrderStatus.PENDING.value,
                OrderStatus.CONFIRMED.value,
                OrderStatus.PREPARING.value,
                OrderStatus.READY.value,
                OrderStatus.OUT_FOR_DELIVERY.value
            ]
            
            active_orders = [
                order for order in all_orders
                if order.get('status') in active_statuses
            ]
            
            # Count orders by status
            pending_orders = len([o for o in active_orders if o.get('status') == OrderStatus.PENDING.value])
            preparing_orders = len([o for o in active_orders if o.get('status') == OrderStatus.PREPARING.value])
            ready_orders = len([o for o in active_orders if o.get('status') == OrderStatus.READY.value])
            
            # Get tables for this venue
            tables = await table_repo.get_by_venue(venue_id)
            active_tables = [t for t in tables if t.get('is_active', False)]
            occupied_tables = [
                t for t in active_tables 
                if t.get('table_status') == TableStatus.OCCUPIED.value
            ]
            
            # Format active orders with details
            formatted_active_orders = []
            for order in active_orders[:10]:  # Limit to 10 most recent
                # Get table number if available
                table_number = None
                if order.get('table_id'):
                    table = await table_repo.get_by_id(order['table_id'])
                    if table:
                        table_number = table.get('table_number')
                
                # Calculate estimated ready time if not set
                estimated_ready_time = order.get('estimated_ready_time')
                if not estimated_ready_time and order.get('created_at'):
                    # Default 20 minutes from creation
                    estimated_ready_time = order['created_at'] + timedelta(minutes=20)
                
                formatted_active_orders.append({
                    "id": order['id'],
                    "order_number": order.get('order_number', 'N/A'),
                    "table_number": table_number,
                    "total_amount": order.get('total_amount', 0),
                    "status": order.get('status', 'unknown'),
                    "created_at": order.get('created_at', datetime.utcnow()).isoformat() if order.get('created_at') else datetime.utcnow().isoformat(),
                    "estimated_ready_time": estimated_ready_time.isoformat() if estimated_ready_time else None,
                    "items_count": len(order.get('items', [])),
                })
            
            return {
                "summary": {
                    "active_orders": len(active_orders),
                    "pending_orders": pending_orders,
                    "preparing_orders": preparing_orders,
                    "ready_orders": ready_orders,
                    "occupied_tables": len(occupied_tables),
                    "total_tables": len(active_tables),
                },
                "active_orders": formatted_active_orders,
            }
            
        except Exception as e:
            logger.error(f"Error getting operator dashboard data: {e}")
            raise
    
    async def get_live_order_status(self, venue_id: str) -> Dict[str, Any]:
        """Get real-time order status for venue"""
        try:
            order_repo = self._get_repo_manager().get_repository('order')
            table_repo = self._get_repo_manager().get_repository('table')
            
            # Get all orders for this venue
            all_orders = await order_repo.get_by_venue(venue_id)
            
            # Filter active orders
            active_statuses = [
                OrderStatus.PENDING.value,
                OrderStatus.CONFIRMED.value,
                OrderStatus.PREPARING.value,
                OrderStatus.READY.value,
                OrderStatus.OUT_FOR_DELIVERY.value
            ]
            
            active_orders = [
                order for order in all_orders
                if order.get('status') in active_statuses
            ]
            
            # Group orders by status
            orders_by_status = defaultdict(list)
            
            for order in active_orders:
                status = order.get('status')
                
                # Get table number if available
                table_number = None
                if order.get('table_id'):
                    table = await table_repo.get_by_id(order['table_id'])
                    if table:
                        table_number = table.get('table_number')
                
                order_data = {
                    "id": order['id'],
                    "order_number": order.get('order_number', 'N/A'),
                    "table_number": table_number,
                    "total_amount": order.get('total_amount', 0),
                    "status": status,
                    "created_at": order.get('created_at', datetime.utcnow()).isoformat() if order.get('created_at') else datetime.utcnow().isoformat(),
                }
                
                orders_by_status[status].append(order_data)
            
            # Calculate summary
            pending_count = len(orders_by_status.get(OrderStatus.PENDING.value, []))
            preparing_count = len(orders_by_status.get(OrderStatus.PREPARING.value, []))
            ready_count = len(orders_by_status.get(OrderStatus.READY.value, []))
            
            return {
                "summary": {
                    "total_active_orders": len(active_orders),
                    "pending_orders": pending_count,
                    "preparing_orders": preparing_count,
                    "ready_orders": ready_count,
                },
                "orders_by_status": dict(orders_by_status)
            }
            
        except Exception as e:
            logger.error(f"Error getting live order status: {e}")
            raise
    
    async def get_live_table_status(self, venue_id: str) -> Dict[str, Any]:
        """Get real-time table status for venue"""
        try:
            table_repo = self._get_repo_manager().get_repository('table')
            
            # Get all tables for this venue
            tables = await table_repo.get_by_venue(venue_id)
            active_tables = [t for t in tables if t.get('is_active', False)]
            
            # Count by status
            status_counts = {
                "available": 0,
                "occupied": 0,
                "reserved": 0,
                "maintenance": 0,
            }
            
            formatted_tables = []
            for table in active_tables:
                status = table.get('table_status', TableStatus.AVAILABLE.value)
                
                # Count status
                if status in status_counts:
                    status_counts[status] += 1
                
                formatted_tables.append({
                    "id": table['id'],
                    "table_number": table.get('table_number'),
                    "capacity": table.get('capacity', 4),
                    "status": status,
                })
            
            return {
                "tables": formatted_tables,
                "summary": {
                    "total_tables": len(active_tables),
                    "available": status_counts["available"],
                    "occupied": status_counts["occupied"],
                    "reserved": status_counts["reserved"],
                    "maintenance": status_counts["maintenance"],
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting live table status: {e}")
            raise
    
    async def get_venue_dashboard_data(self, venue_id: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
        """Get dashboard data for a specific venue with frontend-expected structure"""
        try:
            # Get repositories
            venue_repo = self._get_repo_manager().get_repository('venue')
            order_repo = self._get_repo_manager().get_repository('order')
            table_repo = self._get_repo_manager().get_repository('table')
            menu_item_repo = self._get_repo_manager().get_repository('menu_item')
            menu_category_repo = self._get_repo_manager().get_repository('menu_category')
            user_repo = self._get_repo_manager().get_repository('user')
            
            # Validate venue exists
            venue = await venue_repo.get_by_id(venue_id)
            if not venue:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Venue not found"
                )
            
            # Get today's date range (timezone-aware)
            today = datetime.utcnow().date()
            today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
            today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            # Get all orders for this venue
            all_orders = await order_repo.get_by_venue(venue_id)
            
            # Filter today's orders
            today_orders = []
            for order in all_orders:
                created_at = order.get('created_at')
                if created_at:
                    # Ensure created_at is timezone-aware
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    if today_start <= created_at <= today_end:
                        today_orders.append(order)
            
            # Calculate today's revenue (only paid orders)
            today_revenue = sum(
                order.get('total_amount', 0) 
                for order in today_orders 
                if order.get('payment_status') == PaymentStatus.PAID.value
            )
            
            # Get tables for this venue
            tables = await table_repo.get_by_venue(venue_id)
            active_tables = [t for t in tables if t.get('is_active', False)]
            occupied_tables = [
                t for t in active_tables 
                if t.get('table_status') == TableStatus.OCCUPIED.value
            ]
            
            # Get menu items and categories for this venue
            menu_items = await menu_item_repo.get_by_venue(venue_id)
            active_menu_items = [m for m in menu_items if m.get('is_available', False)]
            menu_categories = await menu_category_repo.get_by_venue(venue_id)
            active_categories = [c for c in menu_categories if c.get('is_active', False)]
            
            # Get staff for this venue
            staff = await user_repo.get_by_venue(venue_id)
            
            # Get recent orders (last 10)
            def get_order_date(order):
                created_at = order.get('created_at')
                if created_at is None:
                    return datetime.min.replace(tzinfo=timezone.utc)
                # Ensure timezone-aware
                if created_at.tzinfo is None:
                    return created_at.replace(tzinfo=timezone.utc)
                return created_at
            
            recent_orders = sorted(
                all_orders,
                key=get_order_date,
                reverse=True
            )[:10]
            
            # Format recent orders with actual data
            formatted_recent_orders = []
            for order in recent_orders:
                # Get table number if available
                table_number = None
                if order.get('table_id'):
                    table = await table_repo.get_by_id(order['table_id'])
                    if table:
                        table_number = table.get('table_number')
                
                formatted_recent_orders.append({
                    "id": order['id'],
                    "order_number": order.get('order_number', 'N/A'),
                    "table_number": table_number,
                    "total_amount": order.get('total_amount', 0),
                    "status": order.get('status', 'unknown'),
                    "payment_status": order.get('payment_status', 'unknown'),
                    "created_at": order.get('created_at', datetime.utcnow()).isoformat() if order.get('created_at') else datetime.utcnow().isoformat(),
                })
            
            # Calculate order status breakdown with colors
            order_status_breakdown = []
            for status in OrderStatus:
                count = len([o for o in all_orders if o.get('status') == status.value])
                if count > 0:
                    order_status_breakdown.append({
                        "status": status.value,
                        "count": count,
                        "color": self._get_status_color(status.value)
                    })
            
            # Calculate table status breakdown with colors
            table_status_breakdown = []
            for status in TableStatus:
                count = len([t for t in active_tables if t.get('table_status') == status.value])
                if count > 0:
                    table_status_breakdown.append({
                        "status": status.value,
                        "count": count,
                        "color": self._get_table_status_color(status.value)
                    })
            
            # Return data in frontend-expected structure
            return {
                "venue_name": venue.get('name', 'Unknown'),
                "venue_id": venue_id,
                "stats": {
                    "today": {
                        "orders_count": len(today_orders),
                        "revenue": today_revenue
                    },
                    "current": {
                        "tables_total": len(active_tables),
                        "tables_occupied": len(occupied_tables),
                        "menu_items_total": len(menu_items),
                        "menu_items_active": len(active_menu_items),
                        "staff_total": len(staff)
                    }
                },
                "recent_orders": formatted_recent_orders,
                "top_menu_items": [],  # No analytics data available
                "revenue_trend": [],   # No historical data available
                "order_status_breakdown": order_status_breakdown,
                "table_status_breakdown": table_status_breakdown,
                # Keep original structure for backward compatibility
                "venue": {
                    "id": venue['id'],
                    "name": venue.get('name', 'Unknown'),
                    "is_active": venue.get('is_active', False),
                    "is_open": venue.get('is_open', False),
                    "status": venue.get('status', 'unknown'),
                },
                "summary": {
                    "today_orders": len(today_orders),
                    "today_revenue": today_revenue,
                    "total_orders": len(all_orders),
                    "total_tables": len(active_tables),
                    "occupied_tables": len(occupied_tables),
                    "total_menu_items": len(menu_items),
                    "active_menu_items": len(active_menu_items),
                    "total_categories": len(menu_categories),
                    "active_categories": len(active_categories),
                    "total_staff": len(staff),
                },
                "analytics": {
                    "order_status_breakdown": {status.value: len([o for o in all_orders if o.get('status') == status.value]) for status in OrderStatus if len([o for o in all_orders if o.get('status') == status.value]) > 0},
                    "table_status_breakdown": {status.value: len([t for t in active_tables if t.get('table_status') == status.value]) for status in TableStatus if len([t for t in active_tables if t.get('table_status') == status.value]) > 0},
                },
                "insights": {
                    "table_occupancy_rate": round((len(occupied_tables) / len(active_tables)) * 100, 1) if active_tables else 0,
                    "menu_availability_rate": round((len(active_menu_items) / len(menu_items)) * 100, 1) if menu_items else 0,
                    "average_order_value": round(today_revenue / len(today_orders), 2) if today_orders else 0,
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting venue dashboard data: {e}")
            raise

    async def get_comprehensive_dashboard_data(self, venue_id: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive dashboard data for admin users with frontend-expected structure"""
        try:
            # Get the base venue dashboard data
            venue_data = await self.get_venue_dashboard_data(venue_id, current_user)
            
            # Transform to match frontend expectations
            comprehensive_data = {
                "venue_name": venue_data["venue"]["name"],
                "venue_id": venue_id,
                "stats": {
                    "today": {
                        "orders_count": venue_data["summary"]["today_orders"],
                        "revenue": venue_data["summary"]["today_revenue"]
                    },
                    "current": {
                        "tables_total": venue_data["summary"]["total_tables"],
                        "tables_occupied": venue_data["summary"]["occupied_tables"],
                        "menu_items_total": venue_data["summary"]["total_menu_items"],
                        "menu_items_active": venue_data["summary"]["active_menu_items"],
                        "staff_total": venue_data["summary"]["total_staff"]
                    }
                },
                "recent_orders": venue_data["recent_orders"],
                "top_menu_items": [],  # No real data available for this
                "revenue_trend": [],   # No historical data available
                "order_status_breakdown": [],
                "table_status_breakdown": []
            }
            
            # Transform analytics data if available
            if "analytics" in venue_data:
                analytics = venue_data["analytics"]
                
                # Transform order status breakdown
                if "order_status_breakdown" in analytics:
                    comprehensive_data["order_status_breakdown"] = [
                        {
                            "status": status,
                            "count": count,
                            "color": self._get_status_color(status)
                        }
                        for status, count in analytics["order_status_breakdown"].items()
                    ]
                
                # Transform table status breakdown
                if "table_status_breakdown" in analytics:
                    comprehensive_data["table_status_breakdown"] = [
                        {
                            "status": status,
                            "count": count,
                            "color": self._get_table_status_color(status)
                        }
                        for status, count in analytics["table_status_breakdown"].items()
                    ]
            
            return comprehensive_data
            
        except Exception as e:
            logger.error(f"Error getting comprehensive dashboard data: {e}")
            raise

    def _get_status_color(self, status: str) -> str:
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

    def _get_table_status_color(self, status: str) -> str:
        """Get color for table status"""
        colors = {
            "available": "#A5D6A7",
            "occupied": "#FFAB91",
            "reserved": "#81D4FA",
            "maintenance": "#FFCC02"
        }
        return colors.get(status.lower(), "#F5F5F5")

    async def get_superadmin_enhanced_venue_data(self, venue_id: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
        """Get venue dashboard data in UI-expected format for SuperAdmin"""
        try:
            # Get the base venue dashboard data
            venue_data = await self.get_venue_dashboard_data(venue_id, current_user)
            
            logger.info(f"Venue data structure: {list(venue_data.keys())}")
            logger.info(f"Summary data: {venue_data.get('summary', {})}")
            
            # For SuperAdmin, return data in the format the UI expects
            # Transform venue data to match SuperAdminDashboardResponse interface
            summary = venue_data.get("summary", {})
            insights = venue_data.get("insights", {})
            venue_info = venue_data.get("venue", {})
            
            enhanced_data = {
                # System stats in the format UI expects
                "system_stats": {
                    "total_workspaces": 1,  # Single workspace for venue view
                    "total_venues": 1,      # Single venue for venue view
                    "total_active_venues": 1,
                    "total_users": summary.get("total_staff", 0),
                    "total_orders": summary.get("total_orders", 0),
                    "total_orders_today": summary.get("today_orders", 0),
                    "total_revenue": 0,  # Not available in venue data
                    "total_revenue_today": summary.get("today_revenue", 0),
                    "active_orders": 0,  # Not available in venue data
                    "total_tables": summary.get("total_tables", 0),
                    "occupied_tables": summary.get("occupied_tables", 0),
                    "total_menu_items": summary.get("total_menu_items", 0),
                    "active_menu_items": summary.get("active_menu_items", 0),
                    "table_occupancy_rate": insights.get("table_occupancy_rate", 0),
                    "avg_order_value": insights.get("average_order_value", 0)
                },
                
                # Workspaces (simplified for venue-based view)
                "workspaces": [{
                    "id": venue_info.get("workspace_id", "default"),
                    "name": "Current Workspace",
                    "venue_count": 1,
                    "user_count": summary.get("total_staff", 0),
                    "total_orders": summary.get("today_orders", 0),
                    "total_revenue": summary.get("today_revenue", 0),
                    "is_active": True,
                    "created_at": datetime.utcnow().isoformat()
                }],
                
                # Venue performance (current venue)
                "venue_performance": [{
                    "id": venue_id,
                    "name": venue_data.get("venue_name", "Unknown"),
                    "total_orders": summary.get("total_orders", 0),
                    "today_orders": summary.get("today_orders", 0),
                    "total_revenue": summary.get("today_revenue", 0),
                    "total_tables": summary.get("total_tables", 0),
                    "occupied_tables": summary.get("occupied_tables", 0),
                    "occupancy_rate": insights.get("table_occupancy_rate", 0),
                    "is_open": venue_info.get("is_open", True),
                    "status": venue_info.get("status", "active")
                }],
                
                # Top menu items (from venue data)
                "top_menu_items": venue_data.get("top_menu_items", []),
                
                # Recent activity (from venue data)
                "recent_activity": venue_data.get("recent_orders", []),
                
                # Analytics (from venue data)
                "analytics": {
                    "order_status_breakdown": venue_data.get("analytics", {}).get("order_status_breakdown", {}),
                    "table_status_breakdown": venue_data.get("analytics", {}).get("table_status_breakdown", {}),
                    "revenue_by_venue": {venue_data.get("venue_name", "Unknown"): summary.get("today_revenue", 0)}
                },
                
                # Mark as SuperAdmin enhanced data
                "is_superadmin_view": True,
                "current_venue_id": venue_id
            }
            
            logger.info(f"Enhanced data created successfully for SuperAdmin")
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error getting SuperAdmin enhanced venue data: {e}")
            logger.error(f"Venue data keys: {list(venue_data.keys()) if 'venue_data' in locals() else 'venue_data not available'}")
            # Fallback to regular venue data if enhancement fails
            return await self.get_venue_dashboard_data(venue_id, current_user)


# Global dashboard service instance
dashboard_service = DashboardService()