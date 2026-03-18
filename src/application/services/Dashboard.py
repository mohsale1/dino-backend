from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from src.application.services.Order import OrderService
from src.application.services.Item import ItemService
from src.application.services.Table import TableService
from src.application.services.Category import CategoryService
from src.repositories.OrganizationRepository import OrganizationRepository

class DashboardService:
    """Dashboard service to aggregate data from multiple sources"""
    
    def __init__(self):
        self.order_service = OrderService()
        self.item_service = ItemService()
        self.table_service = TableService()
        self.category_service = CategoryService()
        self.org_repository = OrganizationRepository()
    
    def get_venue_dashboard(
        self, 
        workspace_id: str,
        organization_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for a venue
        
        Args:
            workspace_id: Workspace ID
            organization_id: Optional organization ID for filtering
            start_date: Optional start date for filtering (ISO format)
            end_date: Optional end date for filtering (ISO format)
        
        Returns:
            Dictionary containing all dashboard data
        """
        
        # Get all orders for the workspace
        orders = self._get_orders(workspace_id, organization_id, start_date, end_date)
        
        # Get all items for the workspace
        items = self.item_service.get_items_by_workspace(workspace_id)
        
        # Get all tables for the workspace
        tables = self.table_service.get_tables_by_workspace(workspace_id)
        
        # Get all categories for the workspace
        categories = self.category_service.get_categories_by_workspace(workspace_id)
        
        # Calculate statistics
        stats = self._calculate_stats(orders, items, tables, categories)
        
        # Get analytics data
        analytics = self._calculate_analytics(orders, items, categories)
        
        # Get recent activity
        recent_activity = self._get_recent_activity(orders)
        
        # Get table statuses
        table_statuses = self._get_table_statuses(tables)
        
        return {
            "success": True,
            "data": {
                "stats": stats,
                "analytics": analytics,
                "recent_activity": recent_activity,
                "table_statuses": table_statuses,
                "summary": {
                    "total_orders": len(orders),
                    "total_revenue": stats.get("total_revenue", 0),
                    "total_tables": len(tables),
                    "total_menu_items": len(items),
                    "active_menu_items": len([i for i in items if i.get("is_available", False)]),
                    "todays_revenue": stats.get("todays_revenue", 0),
                    "todays_orders": stats.get("todays_orders", 0),
                    "avg_order_value": stats.get("avg_order_value", 0),
                    "table_occupancy_rate": stats.get("table_occupancy_rate", 0),
                    "occupied_tables": len([t for t in tables if t.get("status") == "occupied"]),
                    "pending_orders": len([o for o in orders if o.get("status") == "pending"]),
                    "preparing_orders": len([o for o in orders if o.get("status") == "preparing"]),
                    "ready_orders": len([o for o in orders if o.get("status") == "ready"]),
                    "active_orders": len([o for o in orders if o.get("status") in ["pending", "preparing", "ready"]])
                }
            }
        }
    
    def _get_orders(
        self, 
        workspace_id: str, 
        organization_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get orders with optional filters"""
        filters = {"workspace_id": workspace_id}
        
        if organization_id:
            filters["organization_id"] = organization_id
        
        # Get all orders (we'll filter by date in memory for simplicity)
        orders, _, _ = self.order_service.get_paginated(
            page=1,
            page_size=1000,  # Get a large batch
            filters=filters,
            order_by="created_at",
            order_direction="desc"
        )
        
        # Filter by date if provided
        if start_date or end_date:
            filtered_orders = []
            for order in orders:
                order_date = order.get("created_at") or order.get("order_date")
                if order_date:
                    if isinstance(order_date, str):
                        order_date = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                    
                    if start_date:
                        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        if order_date < start:
                            continue
                    
                    if end_date:
                        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        if order_date > end:
                            continue
                    
                    filtered_orders.append(order)
            
            return filtered_orders
        
        return orders
    
    def _calculate_stats(
        self, 
        orders: List[Dict[str, Any]], 
        items: List[Dict[str, Any]], 
        tables: List[Dict[str, Any]],
        categories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate dashboard statistics"""
        
        # Calculate total revenue
        total_revenue = sum(order.get("total_amount", 0) for order in orders)
        
        # Calculate today's stats using timezone-aware UTC date
        today = datetime.now(timezone.utc).date()
        todays_orders = []
        todays_revenue = 0
        
        for order in orders:
            order_date = self._get_order_date(order)
            if order_date is None:
                continue

            # Ensure order_date is timezone-aware before comparing
            if order_date.tzinfo is None:
                order_date = order_date.replace(tzinfo=timezone.utc)

            if order_date.date() == today:
                todays_orders.append(order)
                todays_revenue += order.get("total_amount", 0)
        
        # Calculate average order value
        avg_order_value = total_revenue / len(orders) if orders else 0
        
        # Calculate table occupancy rate using correct 'status' field
        occupied_tables = len([t for t in tables if t.get("status") == "occupied"])
        table_occupancy_rate = (occupied_tables / len(tables) * 100) if tables else 0
        
        return {
            "total_revenue": round(total_revenue, 2),
            "todays_revenue": round(todays_revenue, 2),
            "todays_orders": len(todays_orders),
            "avg_order_value": round(avg_order_value, 2),
            "table_occupancy_rate": round(table_occupancy_rate, 2),
            "total_categories": len(categories),
            "active_items": len([i for i in items if i.get("is_available", False)])
        }
    
    def _calculate_analytics(
        self, 
        orders: List[Dict[str, Any]], 
        items: List[Dict[str, Any]],
        categories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate analytics data"""
        
        # Revenue trend (last 30 days)
        revenue_trend = self._calculate_revenue_trend(orders)
        
        # Order status breakdown
        order_status_breakdown = self._calculate_order_status_breakdown(orders)
        
        # Popular items
        popular_items = self._calculate_popular_items(orders, items)
        
        # Category performance
        category_performance = self._calculate_category_performance(orders, items, categories)
        
        # Payment methods distribution
        payment_methods = self._calculate_payment_methods(orders)
        
        # Peak hours
        peak_hours = self._calculate_peak_hours(orders)
        
        return {
            "revenue_trend": revenue_trend,
            "order_status_breakdown": order_status_breakdown,
            "popular_items": popular_items,
            "category_performance": category_performance,
            "payment_methods": payment_methods,
            "peak_hours": peak_hours
        }
    
    def _calculate_revenue_trend(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate revenue trend for last 30 days"""
        trend = []
        today = datetime.now(timezone.utc).date()
        
        for i in range(29, -1, -1):
            date = today - timedelta(days=i)
            day_orders = []
            for o in orders:
                order_date = self._get_order_date(o)
                if order_date is None:
                    continue
                if order_date.tzinfo is None:
                    order_date = order_date.replace(tzinfo=timezone.utc)
                if order_date.date() == date:
                    day_orders.append(o)
            
            revenue = sum(o.get("total_amount", 0) for o in day_orders)
            
            trend.append({
                "date": date.isoformat(),
                "period": date.strftime("%b %d"),
                "revenue": round(revenue, 2),
                "orders": len(day_orders)
            })
        
        return trend
    
    def _calculate_order_status_breakdown(self, orders: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate order status breakdown"""
        breakdown = {
            "pending": 0,
            "preparing": 0,
            "ready": 0,
            "completed": 0,
            "cancelled": 0
        }
        
        for order in orders:
            status = order.get("status", "pending")
            if status in breakdown:
                breakdown[status] += 1
        
        return breakdown
    
    def _calculate_popular_items(
        self, 
        orders: List[Dict[str, Any]], 
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate popular items based on order data"""
        
        # Create item lookup
        item_lookup = {item.get("id"): item for item in items}
        
        # Count item orders and revenue
        item_stats = {}
        
        for order in orders:
            order_items = order.get("items", [])
            for order_item in order_items:
                item_id = order_item.get("item_id")
                if item_id and item_id in item_lookup:
                    if item_id not in item_stats:
                        item_stats[item_id] = {
                            "orders": 0,
                            "revenue": 0,
                            "quantity": 0
                        }
                    
                    item_stats[item_id]["orders"] += 1
                    item_stats[item_id]["quantity"] += order_item.get("quantity", 1)
                    item_stats[item_id]["revenue"] += order_item.get("total_price", 0)
        
        # Build popular items list
        popular = []
        for item_id, stats in item_stats.items():
            item = item_lookup[item_id]
            popular.append({
                "id": item_id,
                "name": item.get("name", "Unknown"),
                "category": item.get("category_name", "Uncategorized"),
                "orders": stats["orders"],
                "revenue": round(stats["revenue"], 2),
                "quantity": stats["quantity"],
                "rating": item.get("rating", 4.0)
            })
        
        # Sort by revenue and return top 10
        popular.sort(key=lambda x: x["revenue"], reverse=True)
        return popular[:10]
    
    def _calculate_category_performance(
        self, 
        orders: List[Dict[str, Any]], 
        items: List[Dict[str, Any]],
        categories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate category performance"""
        
        # Create category lookup
        category_lookup = {cat.get("id"): cat for cat in categories}
        
        # Create item to category mapping
        item_to_category = {}
        for item in items:
            category_id = item.get("category_id")
            if category_id:
                item_to_category[item.get("id")] = category_id
        
        # Calculate category stats
        category_stats = {}
        
        for order in orders:
            order_items = order.get("items", [])
            for order_item in order_items:
                item_id = order_item.get("item_id")
                if item_id in item_to_category:
                    category_id = item_to_category[item_id]
                    
                    if category_id not in category_stats:
                        category_stats[category_id] = {
                            "orders": 0,
                            "revenue": 0
                        }
                    
                    category_stats[category_id]["orders"] += 1
                    category_stats[category_id]["revenue"] += order_item.get("total_price", 0)
        
        # Build category performance list
        performance = []
        total_revenue = sum(stats["revenue"] for stats in category_stats.values())
        
        for category_id, stats in category_stats.items():
            if category_id in category_lookup:
                category = category_lookup[category_id]
                percentage = (stats["revenue"] / total_revenue * 100) if total_revenue > 0 else 0
                
                performance.append({
                    "category": category.get("name", "Unknown"),
                    "orders": stats["orders"],
                    "revenue": round(stats["revenue"], 2),
                    "percentage": round(percentage, 1)
                })
        
        # Sort by revenue
        performance.sort(key=lambda x: x["revenue"], reverse=True)
        return performance
    
    def _calculate_payment_methods(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate payment methods distribution"""
        
        methods = {}
        total_revenue = 0
        
        for order in orders:
            payment_method = order.get("payment_method", "cash")
            amount = order.get("total_amount", 0)
            
            if payment_method not in methods:
                methods[payment_method] = {
                    "count": 0,
                    "revenue": 0
                }
            
            methods[payment_method]["count"] += 1
            methods[payment_method]["revenue"] += amount
            total_revenue += amount
        
        # Build payment methods list
        payment_list = []
        for method, stats in methods.items():
            percentage = (stats["revenue"] / total_revenue * 100) if total_revenue > 0 else 0
            
            payment_list.append({
                "method": method.capitalize(),
                "count": stats["count"],
                "revenue": round(stats["revenue"], 2),
                "percentage": round(percentage, 1)
            })
        
        # Sort by revenue
        payment_list.sort(key=lambda x: x["revenue"], reverse=True)
        return payment_list
    
    def _calculate_peak_hours(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate peak hours based on order times"""
        
        hours = {i: {"orders": 0, "revenue": 0} for i in range(24)}
        
        for order in orders:
            order_date = self._get_order_date(order)
            if order_date is None:
                continue

            hours[order_date.hour]["orders"] += 1
            hours[order_date.hour]["revenue"] += order.get("total_amount", 0)
        
        # Build peak hours list
        peak_list = []
        for hour, stats in hours.items():
            if stats["orders"] > 0:  # Only include hours with orders
                peak_list.append({
                    "hour": f"{hour:02d}:00",
                    "orders": stats["orders"],
                    "revenue": round(stats["revenue"], 2)
                })
        
        # Sort by orders
        peak_list.sort(key=lambda x: x["orders"], reverse=True)
        return peak_list[:12]  # Return top 12 hours
    
    def _get_recent_activity(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get recent order activity"""
        
        # Sort orders by date (most recent first), treating None dates as oldest
        sorted_orders = sorted(
            orders,
            key=lambda o: self._get_order_date(o) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )
        
        # Return top 10 recent orders
        recent = []
        for order in sorted_orders[:10]:
            order_date = self._get_order_date(order)
            recent.append({
                "id": order.get("id"),
                "order_number": order.get("order_number"),
                "status": order.get("status", "pending"),
                "subtotal": order.get("subtotal", 0),
                "tax_amount": order.get("tax_amount", 0),
                "discount_amount": order.get("discount_amount", 0),
                "total_amount": order.get("total_amount", 0),
                "table_number": order.get("table_number"),
                "venue_name": order.get("venue_name", ""),
                "createdAt": order_date.isoformat() if order_date is not None else None
            })
        
        return recent
    
    def _get_table_statuses(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get table statuses"""
        
        statuses = []
        for table in tables:
            statuses.append({
                "id": table.get("id"),
                "table_number": table.get("table_number"),
                "status": table.get("status", "available"),
                "capacity": table.get("capacity"),
                "area_id": table.get("area_id"),
                "current_order_id": table.get("current_order_id"),
                "occupancy_time": table.get("occupancy_time")
            })
        
        return statuses
    
    def _get_order_date(self, order: Dict[str, Any]) -> Optional[datetime]:
        """Get order date as datetime object, or None if not present"""
        order_date = order.get("created_at") or order.get("order_date")
        
        if isinstance(order_date, str):
            return datetime.fromisoformat(order_date.replace('Z', '+00:00'))
        elif isinstance(order_date, datetime):
            return order_date
        else:
            return None