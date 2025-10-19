"""
Analytics endpoints for venue-specific data
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.core.security import get_current_user
from app.core.logging_config import get_logger
from app.models.dto import ApiResponse

logger = get_logger(__name__)

router = APIRouter()


def _get_dashboard_service():
    """Lazy import of dashboard service to avoid circular imports"""
    from app.services.dashboard_service import dashboard_service
    return dashboard_service


def _get_repo_manager():
    """Lazy import of repository manager to avoid circular imports"""
    from app.core.dependency_injection import get_repository_manager
    return get_repository_manager()


@router.get("/venues/{venue_id}/dashboard", response_model=ApiResponse)
async def get_venue_dashboard_analytics(
    venue_id: str,
    start_date: Optional[str] = Query(None, description="Start date for analytics (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date for analytics (YYYY-MM-DD)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get comprehensive dashboard analytics for a specific venue"""
    logger.info(f"Venue dashboard analytics requested for venue: {venue_id} by user: {current_user.get('id')}")
    
    try:
        # Get user role for logging purposes
        from app.core.security import _get_user_role
        user_role = await _get_user_role(current_user)
        logger.info(f"User role: {user_role}")
        
        # Check if venue exists
        repo_manager = _get_repo_manager()
        venue_repo = repo_manager.get_repository('venue')
        venue = await venue_repo.get_by_id(venue_id)
        
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Venue with ID {venue_id} not found"
            )
        
        # Parse date range if provided
        period_start = None
        period_end = None
        
        if start_date:
            try:
                period_start = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use YYYY-MM-DD"
                )
        
        if end_date:
            try:
                period_end = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use YYYY-MM-DD"
                )
        
        # Default to last 7 days if no dates provided
        if not period_start or not period_end:
            period_end = datetime.utcnow()
            period_start = period_end - timedelta(days=7)
        
        # Get comprehensive analytics data
        analytics_data = await _get_venue_analytics_data(venue_id, period_start, period_end)
        
        logger.info(f"Venue dashboard analytics retrieved for venue: {venue_id}")
        
        return ApiResponse(
            success=True,
            message="Venue dashboard analytics retrieved successfully",
            data=analytics_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving venue dashboard analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load venue dashboard analytics"
        )


@router.get("/venues/{venue_id}/recent-orders", response_model=ApiResponse)
async def get_venue_recent_orders(
    venue_id: str,
    limit: int = Query(10, ge=1, le=50, description="Number of recent orders to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get recent orders for a specific venue"""
    logger.info(f"Recent orders requested for venue: {venue_id} by user: {current_user.get('id')}")
    
    try:
        # Check if venue exists
        repo_manager = _get_repo_manager()
        venue_repo = repo_manager.get_repository('venue')
        venue = await venue_repo.get_by_id(venue_id)
        
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Venue with ID {venue_id} not found"
            )
        
        # Get recent orders
        order_repo = repo_manager.get_repository('order')
        table_repo = repo_manager.get_repository('table')
        
        all_orders = await order_repo.get_by_venue_id(venue_id)
        
        # Sort by created_at and limit
        recent_orders = sorted(
            all_orders,
            key=lambda x: x.get('created_at', datetime.min),
            reverse=True
        )[:limit]
        
        # Format orders with additional details
        formatted_orders = []
        for order in recent_orders:
            # Get table number if available
            table_number = None
            if order.get('table_id'):
                table = await table_repo.get_by_id(order['table_id'])
                if table:
                    table_number = table.get('table_number', 'N/A')
            
            # Calculate time ago
            created_at = order.get('created_at', datetime.utcnow())
            time_ago = _calculate_time_ago(created_at)
            
            formatted_orders.append({
                "id": order['id'],
                "order_number": order.get('order_number', 'N/A'),
                "table_number": str(table_number) if table_number else 'N/A',
                "table_id": order.get('table_id'),
                "items_count": len(order.get('items', [])),
                "total_amount": order.get('total_amount', 0),
                "status": order.get('status', 'unknown'),
                "created_at": created_at.isoformat() if created_at else datetime.utcnow().isoformat(),
                "time_ago": time_ago,
                "customer_name": order.get('customer_name')
            })
        
        return ApiResponse(
            success=True,
            message="Recent orders retrieved successfully",
            data=formatted_orders
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving recent orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load recent orders"
        )


@router.get("/venues/{venue_id}/live-metrics", response_model=ApiResponse)
async def get_venue_live_metrics(
    venue_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get live metrics for a specific venue"""
    logger.info(f"Live metrics requested for venue: {venue_id} by user: {current_user.get('id')}")
    
    try:
        # Check if venue exists
        repo_manager = _get_repo_manager()
        venue_repo = repo_manager.get_repository('venue')
        venue = await venue_repo.get_by_id(venue_id)
        
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Venue with ID {venue_id} not found"
            )
        
        # Get live metrics
        live_metrics = await _get_venue_live_metrics(venue_id)
        
        return ApiResponse(
            success=True,
            message="Live metrics retrieved successfully",
            data=live_metrics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving live metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load live metrics"
        )


@router.get("/venues/{venue_id}/revenue-trend", response_model=ApiResponse)
async def get_venue_revenue_trend(
    venue_id: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    granularity: str = Query("day", regex="^(hour|day|week|month)$", description="Data granularity"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get revenue trend data for a specific venue"""
    logger.info(f"Revenue trend requested for venue: {venue_id} by user: {current_user.get('id')}")
    
    try:
        # Check if venue exists
        repo_manager = _get_repo_manager()
        venue_repo = repo_manager.get_repository('venue')
        venue = await venue_repo.get_by_id(venue_id)
        
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Venue with ID {venue_id} not found"
            )
        
        # Parse dates
        try:
            period_start = datetime.strptime(start_date, "%Y-%m-%d")
            period_end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        # Get revenue trend data
        revenue_trend = await _get_venue_revenue_trend(venue_id, period_start, period_end, granularity)
        
        return ApiResponse(
            success=True,
            message="Revenue trend retrieved successfully",
            data=revenue_trend
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving revenue trend: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load revenue trend"
        )


async def _get_venue_analytics_data(venue_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Get comprehensive analytics data for a venue"""
    try:
        repo_manager = _get_repo_manager()
        order_repo = repo_manager.get_repository('order')
        table_repo = repo_manager.get_repository('table')
        menu_item_repo = repo_manager.get_repository('menu_item')
        
        # Get all orders for the venue in the date range
        all_orders = await order_repo.get_by_venue_id(venue_id)
        
        # Filter orders by date range
        period_orders = [
            order for order in all_orders
            if order.get('created_at') and start_date <= order['created_at'] <= end_date
        ]
        
        # Get today's orders for summary
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        today_orders = [
            order for order in all_orders
            if order.get('created_at') and today_start <= order['created_at'] <= today_end
        ]
        
        # Calculate summary metrics
        from app.models.schemas import PaymentStatus, OrderStatus
        
        total_revenue = sum(
            order.get('total_amount', 0) 
            for order in period_orders 
            if order.get('payment_status') == PaymentStatus.PAID.value
        )
        
        total_orders = len(period_orders)
        average_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Active orders (not completed/cancelled)
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
        
        # Get tables data
        tables = await table_repo.get_by_venue(venue_id)
        active_tables = [t for t in tables if t.get('is_active', False)]
        
        from app.models.schemas import TableStatus
        occupied_tables = [
            t for t in active_tables 
            if t.get('table_status') == TableStatus.OCCUPIED.value
        ]
        
        # Calculate table turnover rate (simplified)
        table_turnover_rate = len(today_orders) / len(active_tables) if len(active_tables) > 0 else 0
        
        # Generate revenue trend data
        revenue_trend = await _generate_revenue_trend(period_orders, start_date, end_date)
        
        # Generate order status breakdown
        order_status_breakdown = _generate_order_status_breakdown(period_orders)
        
        # Get popular items
        popular_items = await _get_popular_items(venue_id, period_orders)
        
        # Generate hourly performance for today
        hourly_performance = _generate_hourly_performance(today_orders)
        
        # Generate performance metrics
        performance_metrics = _generate_performance_metrics(venue_id, period_orders, active_tables)
        
        # Payment method breakdown
        payment_method_breakdown = _generate_payment_breakdown(period_orders)
        
        # Customer satisfaction (placeholder - would need ratings data)
        customer_satisfaction = {
            "average_rating": 0.0,
            "total_reviews": 0,
            "rating_distribution": []
        }
        
        return {
            "venue_id": venue_id,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "average_order_value": average_order_value,
                "active_orders": len(active_orders),
                "customer_count": len(set(order.get('customer_id') for order in period_orders if order.get('customer_id'))),
                "table_turnover_rate": table_turnover_rate
            },
            "revenue_trend": revenue_trend,
            "order_status_breakdown": order_status_breakdown,
            "popular_items": popular_items,
            "hourly_performance": hourly_performance,
            "cafe_performance_metrics": performance_metrics,
            "payment_method_breakdown": payment_method_breakdown,
            "customer_satisfaction": customer_satisfaction
        }
        
    except Exception as e:
        logger.error(f"Error generating venue analytics data: {e}")
        # Return empty/zero data structure for graceful handling
        return {
            "venue_id": venue_id,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_revenue": 0,
                "total_orders": 0,
                "average_order_value": 0,
                "active_orders": 0,
                "customer_count": 0,
                "table_turnover_rate": 0
            },
            "revenue_trend": [],
            "order_status_breakdown": [],
            "popular_items": [],
            "hourly_performance": [],
            "cafe_performance_metrics": [],
            "payment_method_breakdown": [],
            "customer_satisfaction": {
                "average_rating": 0.0,
                "total_reviews": 0,
                "rating_distribution": []
            }
        }


async def _get_venue_live_metrics(venue_id: str) -> Dict[str, Any]:
    """Get live metrics for a venue"""
    try:
        repo_manager = _get_repo_manager()
        order_repo = repo_manager.get_repository('order')
        table_repo = repo_manager.get_repository('table')
        
        # Get today's date range
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Get all orders for venue
        all_orders = await order_repo.get_by_venue_id(venue_id)
        
        # Filter today's orders
        today_orders = [
            order for order in all_orders
            if order.get('created_at') and today_start <= order['created_at'] <= today_end
        ]
        
        # Active orders
        from app.models.schemas import OrderStatus, PaymentStatus
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
        
        pending_orders = len([o for o in active_orders if o.get('status') == OrderStatus.PENDING.value])
        preparing_orders = len([o for o in active_orders if o.get('status') == OrderStatus.PREPARING.value])
        ready_orders = len([o for o in active_orders if o.get('status') == OrderStatus.READY.value])
        
        # Served orders today
        served_orders_today = len([
            o for o in today_orders 
            if o.get('status') == OrderStatus.DELIVERED.value
        ])
        
        # Current revenue today
        current_revenue_today = sum(
            order.get('total_amount', 0) 
            for order in today_orders 
            if order.get('payment_status') == PaymentStatus.PAID.value
        )
        
        # Table status
        tables = await table_repo.get_by_venue(venue_id)
        active_tables = [t for t in tables if t.get('is_active', False)]
        
        from app.models.schemas import TableStatus
        occupied_tables = len([
            t for t in active_tables 
            if t.get('table_status') == TableStatus.OCCUPIED.value
        ])
        
        # Calculate average wait time (simplified)
        wait_times = []
        for order in active_orders:
            if order.get('created_at'):
                wait_time = (datetime.utcnow() - order['created_at']).total_seconds() / 60
                wait_times.append(wait_time)
        
        average_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0
        
        # Kitchen efficiency (simplified - percentage of orders ready within 20 minutes)
        kitchen_efficiency = 85.0  # Placeholder
        
        return {
            "venue_id": venue_id,
            "timestamp": datetime.utcnow().isoformat(),
            "active_orders": len(active_orders),
            "pending_orders": pending_orders,
            "preparing_orders": preparing_orders,
            "ready_orders": ready_orders,
            "served_orders_today": served_orders_today,
            "current_revenue_today": current_revenue_today,
            "tables_occupied": occupied_tables,
            "total_tables": len(active_tables),
            "average_wait_time": average_wait_time,
            "kitchen_efficiency": kitchen_efficiency
        }
        
    except Exception as e:
        logger.error(f"Error getting live metrics: {e}")
        return {
            "venue_id": venue_id,
            "timestamp": datetime.utcnow().isoformat(),
            "active_orders": 0,
            "pending_orders": 0,
            "preparing_orders": 0,
            "ready_orders": 0,
            "served_orders_today": 0,
            "current_revenue_today": 0,
            "tables_occupied": 0,
            "total_tables": 0,
            "average_wait_time": 0,
            "kitchen_efficiency": 0
        }


async def _get_venue_revenue_trend(venue_id: str, start_date: datetime, end_date: datetime, granularity: str) -> List[Dict[str, Any]]:
    """Get revenue trend data for a venue"""
    try:
        repo_manager = _get_repo_manager()
        order_repo = repo_manager.get_repository('order')
        
        # Get all orders for venue in date range
        all_orders = await order_repo.get_by_venue_id(venue_id)
        
        period_orders = [
            order for order in all_orders
            if order.get('created_at') and start_date <= order['created_at'] <= end_date
        ]
        
        return await _generate_revenue_trend(period_orders, start_date, end_date, granularity)
        
    except Exception as e:
        logger.error(f"Error getting revenue trend: {e}")
        return []


async def _generate_revenue_trend(orders: List[Dict], start_date: datetime, end_date: datetime, granularity: str = "day") -> List[Dict[str, Any]]:
    """Generate revenue trend data"""
    try:
        from app.models.schemas import PaymentStatus
        
        # Group orders by date
        revenue_by_date = {}
        
        current_date = start_date
        while current_date <= end_date:
            date_key = current_date.strftime("%Y-%m-%d")
            revenue_by_date[date_key] = {"revenue": 0, "orders": 0}
            
            if granularity == "day":
                current_date += timedelta(days=1)
            elif granularity == "week":
                current_date += timedelta(weeks=1)
            elif granularity == "month":
                # Add one month (simplified)
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            else:  # hour
                current_date += timedelta(hours=1)
        
        # Aggregate order data
        for order in orders:
            if not order.get('created_at'):
                continue
                
            order_date = order['created_at']
            
            if granularity == "day":
                date_key = order_date.strftime("%Y-%m-%d")
            elif granularity == "week":
                # Get start of week
                start_of_week = order_date - timedelta(days=order_date.weekday())
                date_key = start_of_week.strftime("%Y-%m-%d")
            elif granularity == "month":
                date_key = order_date.strftime("%Y-%m-01")
            else:  # hour
                date_key = order_date.strftime("%Y-%m-%d %H:00:00")
            
            if date_key in revenue_by_date:
                revenue_by_date[date_key]["orders"] += 1
                if order.get('payment_status') == PaymentStatus.PAID.value:
                    revenue_by_date[date_key]["revenue"] += order.get('total_amount', 0)
        
        # Convert to list format
        trend_data = []
        for date_key, data in sorted(revenue_by_date.items()):
            average_order_value = data["revenue"] / data["orders"] if data["orders"] > 0 else 0
            
            trend_data.append({
                "date": date_key,
                "revenue": data["revenue"],
                "orders": data["orders"],
                "average_order_value": average_order_value
            })
        
        return trend_data
        
    except Exception as e:
        logger.error(f"Error generating revenue trend: {e}")
        return []


def _generate_order_status_breakdown(orders: List[Dict]) -> List[Dict[str, Any]]:
    """Generate order status breakdown"""
    try:
        status_counts = {}
        total_orders = len(orders)
        
        for order in orders:
            status = order.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Define colors for different statuses
        status_colors = {
            'pending': '#FFF176',
            'confirmed': '#FFCC02',
            'preparing': '#81D4FA',
            'ready': '#C8E6C9',
            'delivered': '#E1BEE7',
            'cancelled': '#FFAB91',
            'unknown': '#F5F5F5'
        }
        
        breakdown = []
        for status, count in status_counts.items():
            percentage = (count / total_orders * 100) if total_orders > 0 else 0
            breakdown.append({
                "status": status,
                "count": count,
                "percentage": percentage,
                "color": status_colors.get(status, '#F5F5F5')
            })
        
        return breakdown
        
    except Exception as e:
        logger.error(f"Error generating order status breakdown: {e}")
        return []


async def _get_popular_items(venue_id: str, orders: List[Dict]) -> List[Dict[str, Any]]:
    """Get popular menu items from orders"""
    try:
        repo_manager = _get_repo_manager()
        menu_item_repo = repo_manager.get_repository('menu_item')
        
        # Count items from orders
        item_counts = {}
        item_revenue = {}
        
        for order in orders:
            for item in order.get('items', []):
                item_id = item.get('menu_item_id')
                if not item_id:
                    continue
                
                quantity = item.get('quantity', 1)
                price = item.get('price', 0)
                
                item_counts[item_id] = item_counts.get(item_id, 0) + quantity
                item_revenue[item_id] = item_revenue.get(item_id, 0) + (price * quantity)
        
        # Get menu item details
        popular_items = []
        total_revenue = sum(item_revenue.values())
        
        for item_id, count in sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            try:
                menu_item = await menu_item_repo.get_by_id(item_id)
                if menu_item:
                    revenue = item_revenue.get(item_id, 0)
                    percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
                    
                    popular_items.append({
                        "menu_item_id": item_id,
                        "name": menu_item.get('name', 'Unknown'),
                        "category": menu_item.get('category', 'Unknown'),
                        "orders": count,
                        "revenue": revenue,
                        "percentage_of_total": percentage,
                        "image_url": menu_item.get('image_url')
                    })
            except Exception as e:
                logger.warning(f"Could not get menu item {item_id}: {e}")
                continue
        
        return popular_items
        
    except Exception as e:
        logger.error(f"Error getting popular items: {e}")
        return []


def _generate_hourly_performance(orders: List[Dict]) -> List[Dict[str, Any]]:
    """Generate hourly performance data"""
    try:
        from app.models.schemas import PaymentStatus
        
        hourly_data = {}
        
        # Initialize 24 hours
        for hour in range(24):
            hour_key = f"{hour:02d}:00"
            hourly_data[hour_key] = {"orders": 0, "revenue": 0}
        
        # Aggregate order data by hour
        for order in orders:
            if not order.get('created_at'):
                continue
                
            hour = order['created_at'].hour
            hour_key = f"{hour:02d}:00"
            
            hourly_data[hour_key]["orders"] += 1
            if order.get('payment_status') == PaymentStatus.PAID.value:
                hourly_data[hour_key]["revenue"] += order.get('total_amount', 0)
        
        # Convert to list and calculate metrics
        performance_data = []
        max_orders = max(data["orders"] for data in hourly_data.values()) if hourly_data else 0
        
        for hour_key, data in sorted(hourly_data.items()):
            average_order_value = data["revenue"] / data["orders"] if data["orders"] > 0 else 0
            is_peak = data["orders"] >= (max_orders * 0.8) if max_orders > 0 else False
            
            performance_data.append({
                "hour": hour_key,
                "orders": data["orders"],
                "revenue": data["revenue"],
                "average_order_value": average_order_value,
                "peak_indicator": is_peak
            })
        
        return performance_data
        
    except Exception as e:
        logger.error(f"Error generating hourly performance: {e}")
        return []


def _generate_performance_metrics(venue_id: str, orders: List[Dict], tables: List[Dict]) -> List[Dict[str, Any]]:
    """Generate performance metrics"""
    try:
        from app.models.schemas import PaymentStatus
        
        # Calculate various metrics
        total_orders = len(orders)
        total_revenue = sum(
            order.get('total_amount', 0) 
            for order in orders 
            if order.get('payment_status') == PaymentStatus.PAID.value
        )
        
        # Table utilization
        total_tables = len(tables)
        table_utilization = (total_orders / total_tables) if total_tables > 0 else 0
        
        # Average order value
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Customer satisfaction (placeholder)
        customer_satisfaction = 85.0
        
        # Order completion rate
        completed_orders = len([o for o in orders if o.get('status') == 'delivered'])
        completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0
        
        metrics = [
            {
                "metric": "Table Utilization",
                "value": table_utilization,
                "max_value": 10.0,  # Max 10 orders per table
                "unit": "orders/table",
                "trend": "stable",
                "percentage_change": 0
            },
            {
                "metric": "Average Order Value",
                "value": avg_order_value,
                "max_value": 1000.0,  # Max expected order value
                "unit": "₹",
                "trend": "up",
                "percentage_change": 5.2
            },
            {
                "metric": "Customer Satisfaction",
                "value": customer_satisfaction,
                "max_value": 100.0,
                "unit": "%",
                "trend": "stable",
                "percentage_change": 1.1
            },
            {
                "metric": "Order Completion Rate",
                "value": completion_rate,
                "max_value": 100.0,
                "unit": "%",
                "trend": "up",
                "percentage_change": 2.3
            }
        ]
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error generating performance metrics: {e}")
        return []


def _generate_payment_breakdown(orders: List[Dict]) -> List[Dict[str, Any]]:
    """Generate payment method breakdown"""
    try:
        from app.models.schemas import PaymentStatus
        
        payment_counts = {}
        payment_revenue = {}
        total_orders = 0
        total_revenue = 0
        
        for order in orders:
            if order.get('payment_status') != PaymentStatus.PAID.value:
                continue
                
            payment_method = order.get('payment_method', 'unknown')
            amount = order.get('total_amount', 0)
            
            payment_counts[payment_method] = payment_counts.get(payment_method, 0) + 1
            payment_revenue[payment_method] = payment_revenue.get(payment_method, 0) + amount
            
            total_orders += 1
            total_revenue += amount
        
        breakdown = []
        for method, count in payment_counts.items():
            revenue = payment_revenue.get(method, 0)
            percentage = (count / total_orders * 100) if total_orders > 0 else 0
            
            breakdown.append({
                "method": method,
                "count": count,
                "revenue": revenue,
                "percentage": percentage
            })
        
        return breakdown
        
    except Exception as e:
        logger.error(f"Error generating payment breakdown: {e}")
        return []


def _calculate_time_ago(timestamp: datetime) -> str:
    """Calculate human-readable time ago"""
    try:
        now = datetime.utcnow()
        diff = now - timestamp
        
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