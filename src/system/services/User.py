from src.base.BaseService import BaseService
from src.repositories.UserRepository import UserRepository
from src.repositories.RoleRepository import RoleRepository
from src.core.Security import get_password_hash
from typing import Dict, Any, List

class SystemUserService(BaseService):
    """System user management service"""
    
    def __init__(self):
        repository = UserRepository("system_users")
        super().__init__(repository)
        self.role_repository = RoleRepository()
    
    def create_system_user(self, data: Dict[str, Any]) -> str:
        """Create new system user with 4-digit ID"""
        # Hash password
        if 'password' in data:
            data['password_hash'] = get_password_hash(data.pop('password'))
        
        # Use custom create method for system users (generates 4-digit ID)
        created_user = self.repository.create_system_user(data)
        return created_user['id']
    
    def get_user_with_role(self, user_id: str) -> Dict[str, Any]:
        """Get user with role information"""
        user = self.get_by_id(user_id)
        
        if not user:
            return None
        
        # Remove password hash
        user.pop('password_hash', None)
        
        # Get role information
        role = self.role_repository.get_by_id(user.get('role_id', ''))
        if role:
            user['role'] = role
        
        return user
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all system users with role information"""
        users = self.get_all()
        
        result = []
        for user in users:
            # Remove password hash
            user.pop('password_hash', None)
            
            # Get role information
            role = self.role_repository.get_by_id(user.get('role_id', ''))
            if role:
                user['role'] = role
            
            result.append(user)
        
        return result
    
    def update_user(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Update system user"""
        # If password is being updated, hash it
        if 'password' in data:
            data['password_hash'] = get_password_hash(data.pop('password'))
        
        return self.update(user_id, data)
    
    def soft_delete_user(self, user_id: str) -> bool:
        """Soft delete system user"""
        return self.soft_delete(user_id)
    
    def restore_user(self, user_id: str) -> bool:
        """Restore a soft-deleted system user"""
        return self.restore(user_id)
    
    def get_paginated_users(
        self,
        page: int = 1,
        page_size: int = 10,
        include_deleted: bool = False,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ):
        """Get paginated system users with role information"""
        items, total, total_pages = self.get_paginated(
            page=page,
            page_size=page_size,
            include_deleted=include_deleted,
            order_by=order_by,
            order_direction=order_direction
        )
        
        # Add role information to each user
        result = []
        for user in items:
            # Remove password hash
            user.pop('password_hash', None)
            
            # Get role information
            role = self.role_repository.get_by_id(user.get('role_id', ''))
            if role:
                user['role'] = role
            
            result.append(user)
        
        return result, total, total_pages
    
    def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        return self.exists("email", email)
    
    def validate_system_role(self, role_id: str) -> bool:
        """Validate that role exists and is a system role (role_type = 0)"""
        role = self.role_repository.get_by_id(role_id)
        
        if not role:
            return False
        
        return role.get('role_type') == 0
    
    def get_users_by_role(self, role_id: str) -> List[Dict[str, Any]]:
        """Get all users with specific role"""
        users = self.repository.get_all(filters={"role_id": role_id})
        
        result = []
        for user in users:
            # Remove password hash
            user.pop('password_hash', None)
            
            # Get role information
            role = self.role_repository.get_by_id(user.get('role_id', ''))
            if role:
                user['role'] = role
            
            result.append(user)
        
        return result