from src.base.BaseService import BaseService
from src.repositories.WorkspaceRepository import WorkspaceRepository
from src.repositories.UserRepository import UserRepository
from src.repositories.OrganizationRepository import OrganizationRepository
from google.cloud import firestore
from typing import Dict, Any, List

class WorkspaceService(BaseService):
    """Workspace service"""
    
    def __init__(self):
        repository = WorkspaceRepository()
        super().__init__(repository)
        self.user_repository = UserRepository("application_users")
        self.organization_repository = OrganizationRepository()
    
    def create_workspace(self, data: Dict[str, Any]) -> str:
        """Create new workspace"""
        # Ensure organization_ids is initialized as empty list if not provided
        if 'organization_ids' not in data:
            data['organization_ids'] = []
        return self.create(data)
    
    def get_workspace_details(self, workspace_id: str) -> Dict[str, Any]:
        """Get workspace with owner and organizations details populated"""
        workspace = self.get_by_id(workspace_id)
        
        if not workspace:
            return None
        
        # Populate owner details from user
        owner_id = workspace.get('owner_id')
        if owner_id:
            owner = self.user_repository.get_by_id(owner_id)
            if owner:
                # Remove sensitive data
                owner.pop('password_hash', None)
                workspace['owner'] = owner
        
        # Populate organizations details
        organization_ids = workspace.get('organization_ids', [])
        if organization_ids:
            organizations = []
            for org_id in organization_ids:
                org = self.organization_repository.get_by_id(org_id)
                if org:
                    organizations.append(org)
            workspace['organizations'] = organizations
        
        return workspace
    
    def add_organization(self, workspace_id: str, organization_id: str) -> bool:
        """Add an organization to workspace's organization_ids list atomically"""
        try:
            self.repository.collection.document(workspace_id).update({
                'organization_ids': firestore.ArrayUnion([organization_id])
            })
            return True
        except Exception:
            return False
    
    def remove_organization(self, workspace_id: str, organization_id: str) -> bool:
        """Remove an organization from workspace's organization_ids list atomically"""
        try:
            self.repository.collection.document(workspace_id).update({
                'organization_ids': firestore.ArrayRemove([organization_id])
            })
            return True
        except Exception:
            return False
    
    def get_organizations(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all organizations for a workspace"""
        workspace = self.get_by_id(workspace_id)
        if not workspace:
            return []
        
        organization_ids = workspace.get('organization_ids', [])
        organizations = []
        
        for org_id in organization_ids:
            org = self.organization_repository.get_by_id(org_id)
            if org:
                organizations.append(org)
        
        return organizations
