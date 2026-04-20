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
        Get paginated list of application users with role name resolved and
        sensitive fields stripped from every record.

        The caller-supplied filters dict is used as-is (workspace_id,
        organization_id, etc. are already set by the route layer).
        is_deleted is appended here only when include_deleted is False so
        the repository does not apply it a second time.
        """
        import math

        if filters is None:
            filters = {}

        # Only add is_deleted to the filter dict when we want to exclude them;
        # BaseRepository.get_paginated already has its own include_deleted guard
        # so we pass include_deleted=True and control the filter ourselves to
        # avoid Firestore duplicate-filter conflicts.
        if not include_deleted:
            filters['is_deleted'] = False

        if search_query:
            # Fetch all matching records, filter in memory, then paginate
            all_items = self.user_repo.get_all(
                filters=filters if filters else None,
                include_deleted=True   # is_deleted already in filters above
            )
            needle = search_query.lower()
            filtered = [
                user for user in all_items
                if needle in (user.get('email') or '').lower()
                or needle in (user.get('first_name') or '').lower()
                or needle in (user.get('last_name') or '').lower()
            ]
            total = len(filtered)
            total_pages = math.ceil(total / page_size) if page_size > 0 else 0
            start = (page - 1) * page_size
            end = start + page_size
            items = filtered[start:end]
        else:
            items, total, total_pages = self.user_repo.get_paginated(
                page=page,
                page_size=page_size,
                filters=filters,
                include_deleted=True,  # is_deleted already in filters above
                order_by=order_by,
                order_direction=order_direction
            )

        return self._enrich_and_sanitize(items), total, total_pages


    
    def get_by_id(self, user_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        user = self.user_repo.get_by_id(user_id)
        
        if user and not include_deleted and user.get('is_deleted', False):
            return None
        
        return user
    
    def _sanitize_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Strip sensitive fields from a user record."""
        sensitive = {'password_hash', 'password', 'reset_token', 'reset_token_expires_at'}
        return {k: v for k, v in user.items() if k not in sensitive}

    def _enrich_and_sanitize(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Resolve role_id -> role name and strip sensitive fields for a list of users.
        Roles are cached in a local dict to avoid redundant Firestore reads.
        """
        role_cache: Dict[str, Dict[str, Any]] = {}
        result = []
        for user in users:
            user = self._sanitize_user(user)
            role_id = user.pop('role_id', None)
            if role_id:
                if role_id not in role_cache:
                    role = self.role_repo.get_by_id(role_id)
                    role_cache[role_id] = role or {}
                role = role_cache[role_id]
                if role:
                    user['role'] = {
                        'id': role.get('id'),
                        'name': role.get('name'),
                        'role_type': role.get('role_type', 1)
                    }
            result.append(user)
        return result

    def get_user_with_role(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a single user with role resolved and sensitive fields stripped."""
        user = self.get_by_id(user_id)

        if not user:
            return None

        users = self._enrich_and_sanitize([user])
        return users[0] if users else None


    
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
        """Check if email already exists (case-insensitive)"""
        users = self.user_repo.get_all(filters={'email': email})
        # Firestore equality filter is case-sensitive; perform a case-insensitive
        # comparison in memory to catch variations in casing.
        needle = email.lower()
        return any((u.get('email') or '').lower() == needle for u in users)
    
    def validate_application_role(self, role_id: str) -> bool:
        """Validate that role exists and is an application role (role_type = 1)"""
        role = self.role_repo.get_by_id(role_id)
        
        if not role:
            return False
        
        # Check if it's an application role (role_type = 1)
        return role.get('role_type') == 1
    
    def get_users_by_role(self, role_id: str, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all users with a specific role, optionally scoped to a workspace"""
        filters: Dict[str, Any] = {
            'role_id': role_id,
            'is_deleted': False
        }
        if workspace_id:
            filters['workspace_id'] = workspace_id
        users = self.user_repo.get_all(filters=filters, include_deleted=True)
        return self._enrich_and_sanitize(users)



    
    def get_users_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all users in a workspace"""
        users = self.user_repo.get_all(filters={
            'workspace_id': workspace_id,
            'is_deleted': False
        }, include_deleted=True)
        return self._enrich_and_sanitize(users)


    
    def get_users_by_organization(self, organization_id: str, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all users in an organization, optionally scoped to a workspace"""
        filters: Dict[str, Any] = {
            'organization_id': organization_id,
            'is_deleted': False
        }
        if workspace_id:
            filters['workspace_id'] = workspace_id
        users = self.user_repo.get_all(filters=filters, include_deleted=True)
        return self._enrich_and_sanitize(users)


