"""
Order Service
Business logic for order management
"""
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.models.entities import OrderStatus
from app.database.repository_manager import get_order_repo, get_menu_item_repo, get_venue_repo
from app.core.logging import get_logger

logger = get_logger(__name__)


class OrderService:
    """Service for order business logic"""
    
    def __init__(self):
        self.repo = get_order_repo()
    
    async def validate_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate order data before creation
        
        Returns:
            Validation result with errors if any
        """
        errors = []
        
        # Validate venue
        venue_id = order_data.get('venue_id')
        if not venue_id:
            errors.append("Venue ID is required")
        else:
            venue_repo = get_venue_repo()
            venue = await venue_repo.get_by_id(venue_id)
            if not venue:
                errors.append("Venue not found")
            elif not venue.get('is_active'):
                errors.append("Venue is not active")
        
        # Validate items
        items = order_data.get('items', [])
        if not items:
            errors.append("Order must contain at least one item")
        else:
            menu_item_repo = get_menu_item_repo()
            total_amount = 0
            
            for item in items:
                menu_item_id = item.get('menu_item_id')
                quantity = item.get('quantity', 0)
                
                if not menu_item_id:
                    errors.append("Menu item ID is required for all items")
                    continue
                
                if quantity <= 0:
                    errors.append(f"Invalid quantity for item {menu_item_id}")
                    continue
                
                # Validate menu item exists and is available
                menu_item = await menu_item_repo.get_by_id(menu_item_id)
                if not menu_item:
                    errors.append(f"Menu item {menu_item_id} not found")
                elif not menu_item.get('is_available'):
                    errors.append(f"Menu item {menu_item.get('name')} is not available")
                else:
                    # Calculate item total
                    item_price = menu_item.get('price', 0)
                    item_total = item_price * quantity
                    total_amount += item_total
            
            # Validate total amount
            if total_amount <= 0:
                errors.append("Order total must be greater than zero")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "total_amount": total_amount if len(errors) == 0 else 0
        }
    
    async def calculate_order_total(self, items: List[Dict[str, Any]]) -> float:
        """Calculate order total from items"""
        menu_item_repo = get_menu_item_repo()
        total = 0.0
        
        for item in items:
            menu_item_id = item.get('menu_item_id')
            quantity = item.get('quantity', 0)
            
            menu_item = await menu_item_repo.get_by_id(menu_item_id)
            if menu_item:
                item_price = menu_item.get('price', 0)
                total += item_price * quantity
        
        return total
    
    async def update_order_status(self, order_id: str, new_status: OrderStatus, user_id: str, notes: Optional[str] = None) -> bool:
        """Update order status with tracking"""
        update_data = {
            "status": new_status.value,
            "status_updated_at": datetime.utcnow(),
            "status_updated_by": user_id
        }
        
        # Add status-specific fields
        if new_status == OrderStatus.CONFIRMED:
            update_data['confirmed_at'] = datetime.utcnow()
        elif new_status == OrderStatus.PREPARING:
            update_data['preparing_at'] = datetime.utcnow()
        elif new_status == OrderStatus.READY:
            update_data['ready_at'] = datetime.utcnow()
        elif new_status == OrderStatus.DELIVERED:
            update_data['delivered_at'] = datetime.utcnow()
        elif new_status == OrderStatus.CANCELLED:
            update_data['cancelled_at'] = datetime.utcnow()
            if notes:
                update_data['cancellation_reason'] = notes
        
        await self.repo.update(order_id, update_data)
        
        logger.info(f"Order {order_id} status updated to {new_status.value} by user {user_id}")
        return True
    
    async def get_order_statistics(self, venue_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get order statistics for a venue"""
        # Get orders for venue
        orders = await self.repo.get_by_venue(venue_id)
        
        # Filter by date range if provided
        if start_date or end_date:
            filtered_orders = []
            for order in orders:
                order_date = order.get('created_at')
                if order_date:
                    if start_date and order_date < start_date:
                        continue
                    if end_date and order_date > end_date:
                        continue
                    filtered_orders.append(order)
            orders = filtered_orders
        
        # Calculate statistics
        total_orders = len(orders)
        total_revenue = sum(order.get('total_amount', 0) for order in orders)
        
        # Count by status
        status_counts = {}
        for order in orders:
            order_status = order.get('status', 'unknown')
            status_counts[order_status] = status_counts.get(order_status, 0) + 1
        
        # Calculate average order value
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        return {
            "venue_id": venue_id,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "average_order_value": avg_order_value,
            "orders_by_status": status_counts,
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            }
        }
    
    async def cancel_order(self, order_id: str, reason: str, user_id: str) -> bool:
        """Cancel an order"""
        order = await self.repo.get_by_id(order_id)
        if not order:
            return False
        
        # Check if order can be cancelled
        current_status = order.get('status')
        if current_status in [OrderStatus.DELIVERED.value, OrderStatus.CANCELLED.value]:
            return False
        
        await self.update_order_status(order_id, OrderStatus.CANCELLED, user_id, reason)
        return True
    
    async def get_active_orders(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get active orders for a venue"""
        all_orders = await self.repo.get_by_venue(venue_id)
        
        active_statuses = [
            OrderStatus.PENDING.value,
            OrderStatus.CONFIRMED.value,
            OrderStatus.PREPARING.value,
            OrderStatus.READY.value
        ]
        
        active_orders = [
            order for order in all_orders
            if order.get('status') in active_statuses
        ]
        
        # Sort by created_at (newest first)
        active_orders.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
        
        return active_orders


# Singleton instance
_order_service = None

def get_order_service() -> OrderService:
    """Get order service singleton"""
    global _order_service
    if _order_service is None:
        _order_service = OrderService()
    return _order_service