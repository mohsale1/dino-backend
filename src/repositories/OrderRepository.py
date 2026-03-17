from src.base.BaseRepository import BaseRepository
from typing import List, Dict, Any

class OrderRepository(BaseRepository):
    """Order repository"""
    
    def __init__(self):
        super().__init__("orders")
    
    def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all orders by workspace"""
        return self.get_all(filters={"workspace_id": workspace_id})
    
    def get_by_organization(self, organization_id: str) -> List[Dict[str, Any]]:
        """Get all orders by organization"""
        return self.get_all(filters={"organization_id": organization_id})
    
    def get_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all orders by status"""
        return self.get_all(filters={"status": status})