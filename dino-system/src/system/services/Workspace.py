from src.base.BaseService import BaseService
from src.repositories.WorkspaceRepository import WorkspaceRepository
from src.repositories.OrganizationRepository import OrganizationRepository
from src.repositories.UserRepository import UserRepository
from typing import Dict, Any, Optional
from google.cloud import firestore as fs

class WorkspaceService(BaseService):
    def __init__(self):
        repository = WorkspaceRepository()
        super().__init__(repository)
    def create_workspace(self, data):
        result = self.create(data)
        if isinstance(result, dict):
            return result.get('id')
        return result
    def get_workspace_details(self, workspace_id):
        workspace = self.get_by_id(workspace_id)
        if not workspace:
            return None
        owner_id = workspace.get('owner_id')
        if owner_id:
            user_repo = UserRepository('application_users')
            owner = user_repo.get_by_id(owner_id)
            if owner:
                owner.pop('password_hash', None)
                workspace['owner'] = owner
        org_ids = workspace.get('organization_ids', [])
        if org_ids:
            from src.repositories.OrganizationRepository import OrganizationRepository
            org_repo = OrganizationRepository()
            orgs = [org_repo.get_by_id(oid) for oid in org_ids]
            workspace['organizations'] = [o for o in orgs if o]
        return workspace
    def add_organization(self, workspace_id, organization_id):
        return self.repository.update(workspace_id, {'organization_ids': fs.ArrayUnion([organization_id])})
    def remove_organization(self, workspace_id, organization_id):
        return self.repository.update(workspace_id, {'organization_ids': fs.ArrayRemove([organization_id])})
    def get_organizations(self, workspace_id):
        workspace = self.get_by_id(workspace_id)
        if not workspace:
            return []
        from src.repositories.OrganizationRepository import OrganizationRepository
        org_repo = OrganizationRepository()
        return [org_repo.get_by_id(oid) for oid in workspace.get('organization_ids', []) if org_repo.get_by_id(oid)]
    def update_billing_info(self, workspace_id, billing_info):
        return self.update(workspace_id, {'billing_info': billing_info})
