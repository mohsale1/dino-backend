from src.base.BaseService import BaseService
from src.repositories.OrganizationRepository import OrganizationRepository
from typing import Dict, Any, List

class OrganizationService(BaseService):
    """Organization service"""
    
    def __init__(self):
        repository = OrganizationRepository()
        super().__init__(repository)
    
    def get_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all organizations in a workspace"""
        return self.repository.get_by_workspace(workspace_id)