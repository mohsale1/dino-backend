from src.base.BaseRepository import BaseRepository
from typing import List, Dict, Any

class WorkspaceRepository(BaseRepository):
    """Workspace repository"""
    
    def __init__(self):
        super().__init__("workspaces")
    
    def get_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        """Get all workspaces by owner"""
        return self.get_all(filters={"owner_id": owner_id})