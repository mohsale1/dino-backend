"""
Application User Service
Handles business logic for application user management
"""
from src.repositories.UserRepository import UserRepository
from src.repositories.RoleRepository import RoleRepository
from src.core.Security import get_password_hash
from typing import Dict, Any, List, Optional, Tuple

class ApplicationUserService:
    def __init__(self):
        self.user_repo = UserRepository('application_users')
        self.role_repo = RoleRepository()
    
    def create_application_user(self, user_data: Dict[str, Any]) -> str:
        """
        Create a new application user
        
        Args:
            user_data: Dictionary containing user information
            
        Returns:
            str: Created user ID
        """
        # Hash password if provided, store under correct key
        if 'password' in user_data:
            user_data['password_hash'] = get_password_hash(user_data.pop('password'))
        
        # Set default values
        user_data['is_active'] = user_data.get('is_active', True)
        user_data['is_deleted'] = False
        
        return self.user_repo.create(user_data)
    
    def get_paginated_users(
        self,
        page: int = 1,
        page_size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        search_query: Optional[str] = None,
        include_deleted: bool = False,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Get paginated list of application users
        
        Args:
            page: Page number
            page_size: Number of items per page
            filters: Additional filters
            search_query: Search query for name/email
            include_deleted: Include soft-deleted users
            order_by: Field to order by
            order_direction: Order direction (asc/desc)
            
        Returns:
            Tuple of (items, total_count, total_pages)
        """
        # Build filters
        if filters is None:
            filters = {}
        
        if not include_deleted:
            filters['is_deleted'] = False
        
        # Add search functionality
        if search_query:
            # This would need to be implemented in the repository
            # For now, we'll get all and filter in memory (not ideal for production)
            pass
        
        return self.user_repo.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=order_by,
            order_direction=order_direction
        )
    
    def get_by_id(self, user_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        user = self.user_repo.get_by_id(user_id)
        
        if user and not include_deleted and user.get('is_deleted', False):
            return None
        
        return user
    
    def get_user_with_role(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user with role information"""
        user = self.get_by_id(user_id)
        
        if not user:
            return None
        
        # Get role information
        if user.get('role_id'):
            role = self.role_repo.get_by_id(user['role_id'])
            if role:
                user['role'] = {
                    'id': role['id'],
                    'name': role['name'],
                    'role_type': role.get('role_type', 1)
                }
        
        return user
    
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user"""
        # Hash password if being updated, store under correct key
        if 'password' in update_data:
            update_data['password_hash'] = get_password_hash(update_data.pop('password'))
        
        return self.user_repo.update(user_id, update_data)
    
    def soft_delete_user(self, user_id: str) -> bool:
        """Soft delete user"""
        return self.user_repo.update(user_id, {
            'is_deleted': True,
            'is_active': False
        })
    
    def restore_user(self, user_id: str) -> bool:
        """Restore soft-deleted user"""
        return self.user_repo.update(user_id, {
            'is_deleted': False,
            'is_active': True
        })
    
    def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        users = self.user_repo.get_all(filters={'email': email})
        return len(users) > 0
    
    def validate_application_role(self, role_id: str) -> bool:
        """Validate that role exists and is an application role (role_type = 1)"""
        role = self.role_repo.get_by_id(role_id)
        
        if not role:
            return False
        
        # Check if it's an application role (role_type = 1)
        return role.get('role_type') == 1
    
    def get_users_by_role(self, role_id: str) -> List[Dict[str, Any]]:
        """Get all users with a specific role"""
        return self.user_repo.get_all(filters={
            'role_id': role_id,
            'is_deleted': False
        })
    
    def get_users_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all users in a workspace"""
        return self.user_repo.get_all(filters={
            'workspace_id': workspace_id,
            'is_deleted': False
        })
    
    def get_users_by_organization(self, organization_id: str) -> List[Dict[str, Any]]:
        """Get all users in an organization"""
        return self.user_repo.get_all(filters={
            'organization_id': organization_id,
            'is_deleted': False
        })