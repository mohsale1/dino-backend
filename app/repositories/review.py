"""
Review Repository
Data access layer for review collection
"""
from typing import List, Dict, Any

from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReviewRepository(BaseRepository):
    """Repository for review operations"""
    
    def __init__(self):
        super().__init__("reviews")
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        """Get reviews by venue"""
        return await self.query([('venue_id', '==', venue_id)])
    
    async def get_by_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get reviews by customer"""
        return await self.query([('customer_id', '==', customer_id)])
    
    async def get_by_order(self, order_id: str) -> List[Dict[str, Any]]:
        """Get reviews by order"""
        return await self.query([('order_id', '==', order_id)])


def get_review_repository() -> ReviewRepository:
    """Get review repository singleton"""
    global _review_repo
    if '_review_repo' not in globals():
        globals()['_review_repo'] = ReviewRepository()
    return globals()['_review_repo']