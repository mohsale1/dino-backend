from src.base.BaseRepository import BaseRepository
from typing import List, Dict, Any

class OrganizationRepository(BaseRepository):
    """Organization repository"""
    
    def __init__(self):
        super().__init__("organizations")
    
    def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all organizations by workspace"""
        return self.get_all(filters={"workspace_id": workspace_id})