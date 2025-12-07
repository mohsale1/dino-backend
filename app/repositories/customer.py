"""
Customer Repository
Data access layer for customer collection
"""
from typing import List, Dict, Any, Optional

from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class CustomerRepository(BaseRepository):
    """Repository for customer operations"""
    
    def __init__(self):
        super().__init__("customers")
    
    async def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get customer by phone"""
        results = await self.query([('phone', '==', phone)])
        return results[0] if results else None
    
    
    async def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search customers by name"""
        all_customers = await self.get_all()
        name_lower = name.lower()
        return [
            customer for customer in all_customers
            if name_lower in customer.get('name', '').lower()
        ]
    
    async def get_top_customers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top customers by total orders"""
        all_customers = await self.get_all()
        sorted_customers = sorted(
            all_customers,
            key=lambda x: x.get('total_orders', 0),
            reverse=True
        )
        return sorted_customers[:limit]


# Singleton instance
_customer_repo = None

def get_customer_repository() -> CustomerRepository:
    """Get customer repository singleton"""
    global _customer_repo
    if _customer_repo is None:
        _customer_repo = CustomerRepository()
    return _customer_repo