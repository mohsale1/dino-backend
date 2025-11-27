"""
Role Repository
Data access layer for role collection
"""
from typing import List, Dict, Any, Optional

from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class RoleRepository(BaseRepository):
    """Repository for role operations"""
    
    def __init__(self):
        super().__init__("roles")
    
    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get role by name"""
        results = await self.query([('name', '==', name)])
        return results[0] if results else None
    
    async def get_system_roles(self) -> List[Dict[str, Any]]:
        """Get system roles"""
        return await self.query([('is_system_role', '==', True)])
    
    async def get_custom_roles(self) -> List[Dict[str, Any]]:
        """Get custom roles"""
        all_roles = await self.get_all()
        return [role for role in all_roles if not role.get('is_system_role', False)]
    
    async def assign_permissions(self, role_id: str, permission_ids: List[str]) -> bool:
        """Assign permissions to role (replaces existing)"""
        try:
            await self.update(role_id, {'permission_ids': permission_ids})
            return True
        except Exception as e:
            logger.error(f"Error assigning permissions to role: {e}")
            raise
    
    async def add_permissions(self, role_id: str, permission_ids: List[str]) -> bool:
        """Add permissions to role (keeps existing)"""
        try:
            role = await self.get_by_id(role_id)
            if not role:
                return False
            
            current_permissions = set(role.get('permission_ids', []))
            new_permissions = current_permissions.union(set(permission_ids))
            
            await self.update(role_id, {'permission_ids': list(new_permissions)})
            return True
        except Exception as e:
            logger.error(f"Error adding permissions to role: {e}")
            raise
    
    async def remove_permissions(self, role_id: str, permission_ids: List[str]) -> bool:
        """Remove permissions from role"""
        try:
            role = await self.get_by_id(role_id)
            if not role:
                return False
            
            current_permissions = set(role.get('permission_ids', []))
            remaining_permissions = current_permissions - set(permission_ids)
            
            await self.update(role_id, {'permission_ids': list(remaining_permissions)})
            return True
        except Exception as e:
            logger.error(f"Error removing permissions from role: {e}")
            raise
    
    async def get_role_permissions(self, role_id: str) -> List[Dict[str, Any]]:
        """Get full permission objects for a role"""
        role = await self.get_by_id(role_id)
        if not role:
            return []
        
        permission_ids = role.get('permission_ids', [])
        if not permission_ids:
            return []
        
        # Get permissions from permissions collection
        from app.database.repository_manager import get_permission_repo
        perm_repo = get_permission_repo()
        
        permissions = []
        for perm_id in permission_ids:
            permission = await perm_repo.get_by_id(perm_id)
            if permission:
                permissions.append(permission)
        
        return permissions
    
    async def get_users_with_role(self, role_id: str) -> List[Dict[str, Any]]:
        """Get users with specific role"""
        from app.database.repository_manager import get_user_repo
        user_repo = get_user_repo()
        return await user_repo.get_by_role(role_id)
    
    async def list_roles(self, 
                        filters: Optional[Dict[str, Any]] = None,
                        page: int = 1,
                        page_size: int = 10) -> tuple:
        """List roles with pagination and filtering"""
        # Build query filters
        query_filters = []
        
        if filters:
            for field, value in filters.items():
                if value is not None and field != 'search':
                    query_filters.append((field, '==', value))
        
        # Get all matching roles (we'll handle pagination in memory for simplicity)
        if query_filters:
            all_roles = await self.query(query_filters)
        else:
            all_roles = await self.get_all()
        
        # Apply search filter
        if filters and filters.get('search'):
            search_term = filters['search'].lower()
            all_roles = [
                role for role in all_roles
                if search_term in role.get('name', '').lower() or
                   search_term in role.get('description', '').lower()
            ]
        
        # Get total count
        total = len(all_roles)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_roles = all_roles[start_idx:end_idx]
        
        return paginated_roles, total
    
    async def get_role_statistics(self) -> Dict[str, Any]:
        """Get role statistics"""
        all_roles = await self.get_all()
        
        stats = {
            "total_roles": len(all_roles),
            "users_by_role": {}
        }
        
        # Count users by role
        for role in all_roles:
            users = await self.get_users_with_role(role['id'])
            stats["users_by_role"][role['name']] = len(users)
        
        return stats


# Singleton instance
_role_repo = None

def get_role_repository() -> RoleRepository:
    """Get role repository singleton"""
    global _role_repo
    if _role_repo is None:
        _role_repo = RoleRepository()
    return _role_repo