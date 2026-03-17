from src.base.BaseService import BaseService
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository
from typing import Dict, Any, List

class RoleService(BaseService):
    """Role management service"""
    
    def __init__(self):
        repository = RoleRepository()
        super().__init__(repository)
    
    def create_role(self, data: Dict[str, Any]) -> str:
        """Create new role"""
        return self.create(data)
    
    def get_all_roles(self) -> List[Dict[str, Any]]:
        """Get all roles"""
        return self.get_all()
    
    def get_roles_by_type(self, role_type: int) -> List[Dict[str, Any]]:
        """Get roles by type (0=System, 1=Application)"""
        return self.repository.get_by_type(role_type)
    
    def update_role(self, role_id: str, data: Dict[str, Any]) -> bool:
        """Update role"""
        return self.update(role_id, data)
    
    def soft_delete_role(self, role_id: str) -> bool:
        """Soft delete role"""
        return self.soft_delete(role_id)
    
    def restore_role(self, role_id: str) -> bool:
        """Restore a soft-deleted role"""
        return self.restore(role_id)
    
    def get_role_by_id(self, role_id: str, include_deleted: bool = False) -> Dict[str, Any]:
        """Get role by ID (can include deleted)"""
        return self.get_by_id(role_id, include_deleted)
    
    def role_exists(self, name: str, role_type: int) -> bool:
        """Check if role exists with given name and type"""
        role = self.repository.get_by_name_and_type(name, role_type)
        return role is not None
    
    def add_permissions(self, role_id: str, permissions: List[str]) -> bool:
        """Add permissions to role"""
        role = self.get_by_id(role_id)
        
        if not role:
            return False
        
        current_permissions = role.get('permissions', [])
        
        # Add new permissions (avoid duplicates)
        updated_permissions = list(set(current_permissions + permissions))
        
        return self.update(role_id, {'permissions': updated_permissions})
    
    def remove_permissions(self, role_id: str, permissions: List[str]) -> bool:
        """Remove permissions from role"""
        role = self.get_by_id(role_id)
        
        if not role:
            return False
        
        current_permissions = role.get('permissions', [])
        
        # Remove specified permissions
        updated_permissions = [p for p in current_permissions if p not in permissions]
        
        return self.update(role_id, {'permissions': updated_permissions})
    
    def is_role_in_use(self, role_id: str) -> bool:
        """Check if role is assigned to any users"""
        # Check system users
        system_user_repo = UserRepository("system_users")
        system_users = system_user_repo.get_all(filters={"role_id": role_id})
        
        if system_users:
            return True
        
        # Check application users
        app_user_repo = UserRepository("application_users")
        app_users = app_user_repo.get_all(filters={"role_id": role_id})
        
        return len(app_users) > 0
    
    def get_users_by_role(self, role_id: str) -> List[Dict[str, Any]]:
        """Get all users assigned to a role"""
        users = []
        
        # Get system users with this role
        system_user_repo = UserRepository("system_users")
        system_users = system_user_repo.get_all(filters={"role_id": role_id})
        
        for user in system_users:
            user['user_type'] = 'system'
            # Remove password hash
            user.pop('password_hash', None)
            users.append(user)
        
        # Get application users with this role
        app_user_repo = UserRepository("application_users")
        app_users = app_user_repo.get_all(filters={"role_id": role_id})
        
        for user in app_users:
            user['user_type'] = 'application'
            # Remove password hash
            user.pop('password_hash', None)
            users.append(user)
        
        return users
    
    def get_default_permissions_for_role(self, role_name: str, role_type: int) -> List[str]:
        """Get default permissions for predefined roles"""
        
        # System roles (role_type = 0)
        system_role_permissions = {
            "SuperAdmin": ["system:*"],
            "BillingManager": ["system:billing:*", "system:workspaces:read"],
            "MarketingAgent": ["system:registration:*"]
        }
        
        # Application roles (role_type = 1)
        application_role_permissions = {
            "Owner": ["workspace:*"],
            "Admin": [
                "dashboard:*",
                "items:*",
                "categories:*",
                "areas:*",
                "tables:*",
                "orders:*",
                "reviews:*",
                "users:read",
                "users:update",
                "organization:read",
                "workspace:read"
            ],
            "Operator": [
                "dashboard:read",
                "items:read",
                "categories:read",
                "areas:read",
                "tables:read",
                "orders:read",
                "orders:update",
                "orders:status",
                "reviews:read",
                "organization:read",
                "workspace:read"
            ]
        }
        
        if role_type == 0:
            return system_role_permissions.get(role_name, [])
        elif role_type == 1:
            return application_role_permissions.get(role_name, [])
        
        return []