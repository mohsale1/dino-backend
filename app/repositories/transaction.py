"""
Transaction Repository
"""
from typing import List, Dict, Any
from app.repositories.base import BaseRepository

class TransactionRepository(BaseRepository):
    def __init__(self):
        super().__init__("transactions")
    
    async def get_by_venue(self, venue_id: str) -> List[Dict[str, Any]]:
        return await self.query([('venue_id', '==', venue_id)])
    
    async def get_by_order(self, order_id: str) -> List[Dict[str, Any]]:
        return await self.query([('order_id', '==', order_id)])

def get_transaction_repository() -> TransactionRepository:
    if '_transaction_repo' not in globals():
        globals()['_transaction_repo'] = TransactionRepository()
    return globals()['_transaction_repo']