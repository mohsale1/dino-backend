from src.base.BaseService import BaseService
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository
from typing import Dict, Any, List

class RoleService(BaseService):
    def __init__(self):
        repository = RoleRepository()
        super().__init__(repository)
    def create_role(self, data):
        return self.create(data)
    def get_all_roles(self):
        return self.get_all()
    def get_roles_by_type(self, role_type):
        return self.repository.get_by_type(role_type)
    def update_role(self, role_id, data):
        return self.update(role_id, data)
    def soft_delete_role(self, role_id):
        return self.soft_delete(role_id)
    def restore_role(self, role_id):
        return self.restore(role_id)
    def get_role_by_id(self, role_id, include_deleted=False):
        return self.get_by_id(role_id, include_deleted)
    def role_exists(self, name, role_type):
        return self.repository.get_by_name_and_type(name, role_type) is not None
    def add_permissions(self, role_id, permissions):
        from google.cloud import firestore
        return self.repository.update(role_id, {'permissions': firestore.ArrayUnion(permissions)})
    def remove_permissions(self, role_id, permissions):
        from google.cloud import firestore
        return self.repository.update(role_id, {'permissions': firestore.ArrayRemove(permissions)})
    def is_role_in_use(self, role_id):
        system_repo = UserRepository('system_users')
        app_repo = UserRepository('application_users')
        system_users = system_repo.get_all(filters={'role_id': role_id})
        if system_users:
            return True
        app_users = app_repo.get_all(filters={'role_id': role_id})
        return bool(app_users)
    def get_users_by_role(self, role_id):
        system_repo = UserRepository('system_users')
        app_repo = UserRepository('application_users')
        system_users = system_repo.get_all(filters={'role_id': role_id})
        app_users = app_repo.get_all(filters={'role_id': role_id})
        return {'system_users': system_users, 'application_users': app_users}
    def get_default_permissions_for_role(self, role_name):
        defaults = {
            'SuperAdmin': ['system:*'],
            'BillingManager': ['system:billing:*', 'system:workspaces:read'],
            'MarketingAgent': ['system:registration:*'],
            'Owner': ['workspace:*'],
            'Admin': ['dashboard:*', 'items:*', 'categories:*', 'areas:*', 'tables:*', 'orders:*', 'reviews:*', 'users:read', 'users:update', 'organization:read', 'workspace:read'],
            'Operator': ['dashboard:read', 'items:read', 'categories:read', 'areas:read', 'tables:read', 'orders:read', 'orders:update', 'orders:status', 'reviews:read', 'organization:read', 'workspace:read']
        }
        return defaults.get(role_name, [])