"""
Order Repository
Data access layer for order collection
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class OrderRepository(BaseRepository):
    """Repository for order operations"""
    
    def __init__(self):
        super().__init__("orders")
    
    async def get_by_venue(self, venue_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get orders by venue"""
        return await self.query([('venue_id', '==', venue_id)], limit=limit)
    
    async def get_by_customer(self, customer_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get orders by customer"""
        return await self.query([('customer_id', '==', customer_id)], limit=limit)
    
    async def get_by_status(self, venue_id: str, status: str) -> List[Dict[str, Any]]:
        """Get orders by status"""
        return await self.query([
            ('venue_id', '==', venue_id),
            ('status', '==', status)
        ])
    
    async def get_active_orders(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get active orders"""
        all_orders = await self.get_by_venue(venue_id)
        active_statuses = ['pending', 'confirmed', 'preparing', 'ready']
        return [
            order for order in all_orders
            if order.get('status') in active_statuses
        ]
    
    async def update_status(self, order_id: str, status: str) -> bool:
        """Update order status"""
        try:
            await self.update(order_id, {'status': status})
            return True
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            raise


def get_order_repository() -> OrderRepository:
    """Get order repository singleton"""
    global _order_repo
    if '_order_repo' not in globals():
        globals()['_order_repo'] = OrderRepository()
    return globals()['_order_repo']