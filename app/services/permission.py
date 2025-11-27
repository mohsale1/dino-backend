"""
Permission Service
Business logic for permission management
"""
from typing import List, Dict, Any, Optional

from app.repositories.permission import PermissionRepository
from app.database.repository_manager import get_user_repo, get_role_repo
from app.core.logging import get_logger

logger = get_logger(__name__)


class PermissionService:
    """Service for permission business logic"""
    
    def __init__(self):
        self.repo = PermissionRepository()
        self.user_repo = get_user_repo()
        self.role_repo = get_role_repo()
    
    async def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """Get all permissions for a specific user"""
        user = await self.user_repo.get_by_id(user_id)
        
        if not user:
            return {
                "user_id": user_id,
                "role": None,
                "permissions": [],
                "total_permissions": 0
            }
        
        # Get user's role
        user_role_id = user.get('role_id')
        if not user_role_id:
            return {
                "user_id": user_id,
                "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                "user_email": user.get('email'),
                "role": None,
                "permissions": [],
                "total_permissions": 0
            }
        
        # Get role
        role_data = await self.role_repo.get_by_id(user_role_id)
        if not role_data:
            logger.warning(f"User {user_id} has invalid role_id: {user_role_id}")
            return {
                "user_id": user_id,
                "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                "user_email": user.get('email'),
                "role": {"id": user_role_id, "name": "Invalid Role", "exists": False},
                "permissions": [],
                "total_permissions": 0
            }
        permission_ids = role_data.get('permission_ids', [])
        
        # Get permissions
        permissions = []
        for perm_id in permission_ids:
            permission = await self.repo.get_by_id(perm_id)
            if permission:
                roles = await self.repo.get_roles_with_permission(perm_id)
                permission['roles_count'] = len(roles)
                permissions.append(permission)
        
        return {
            "user_id": user_id,
            "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "user_email": user.get('email'),
            "role": {
                "id": user_role_id,
                "name": role_data.get('name', 'Unknown'),
                "display_name": role_data.get('display_name', role_data.get('name', 'Unknown')),
                "description": role_data.get('description', ''),
                "exists": True
            },
            "permissions": permissions,
            "total_permissions": len(permissions)
        }
    
    async def get_role_permissions(self, role_id: str) -> Dict[str, Any]:
        """Get all permissions for a specific role"""
        role_data = await self.role_repo.get_by_id(role_id)
        if not role_data:
            return None
        permission_ids = role_data.get('permission_ids', [])
        
        # Get permissions
        permissions = []
        missing_permissions = []
        
        for perm_id in permission_ids:
            permission = await self.repo.get_by_id(perm_id)
            if permission:
                roles = await self.repo.get_roles_with_permission(perm_id)
                permission['roles_count'] = len(roles)
                permissions.append(permission)
            else:
                missing_permissions.append(perm_id)
                logger.warning(f"Permission {perm_id} not found for role {role_id}")
        
        # Get users count for this role
        users_with_role = await self.user_repo.get_by_role(role_id)
        users_count = len(users_with_role)
        
        return {
            "role_id": role_id,
            "role_name": role_data.get('name', 'Unknown'),
            "role_display_name": role_data.get('display_name', role_data.get('name', 'Unknown')),
            "role_description": role_data.get('description', ''),
            "permissions": permissions,
            "total_permissions": len(permissions),
            "users_with_role": users_count,
            "missing_permissions": missing_permissions if missing_permissions else None
        }
    
    async def check_user_permissions(self, user_id: str, permission_names: List[str]) -> Dict[str, Any]:
        """Check if user has specific permissions"""
        user_perms_data = await self.get_user_permissions(user_id)
        user_permission_names = [perm['name'] for perm in user_perms_data.get('permissions', [])]
        
        # Check each requested permission
        permission_check = {}
        for perm_name in permission_names:
            permission_check[perm_name] = perm_name in user_permission_names
        
        return {
            "user_id": user_id,
            "user_name": user_perms_data.get('user_name'),
            "role": user_perms_data.get('role'),
            "requested_permissions": permission_names,
            "permission_results": permission_check,
            "has_all_permissions": all(permission_check.values()),
            "has_any_permissions": any(permission_check.values()),
            "missing_permissions": [perm for perm, has_perm in permission_check.items() if not has_perm]
        }
    
    async def validate_user_access(self, user_id: str, resource: str, action: str) -> Dict[str, Any]:
        """Validate if user has access to perform a specific action on a resource"""
        user_perms_data = await self.get_user_permissions(user_id)
        permissions = user_perms_data.get('permissions', [])
        
        # Check for specific permission
        permission_name = f"{resource}.{action}"
        has_permission = any(
            perm.get('name') == permission_name or 
            (perm.get('resource') == resource and perm.get('action') == action)
            for perm in permissions
        )
        
        # Also check for wildcard permissions
        wildcard_permissions = [
            f"{resource}.*",
            f"*.{action}",
            "*.*"
        ]
        
        has_wildcard = any(
            perm.get('name') in wildcard_permissions
            for perm in permissions
        )
        
        has_access = has_permission or has_wildcard
        
        return {
            "user_id": user_id,
            "user_name": user_perms_data.get('user_name'),
            "role": user_perms_data.get('role'),
            "resource": resource,
            "action": action,
            "permission_name": permission_name,
            "has_access": has_access,
            "access_type": "direct" if has_permission else ("wildcard" if has_wildcard else "none"),
            "matching_permissions": [
                perm for perm in permissions 
                if perm.get('name') == permission_name or 
                   (perm.get('resource') == resource and perm.get('action') == action) or
                   perm.get('name') in wildcard_permissions
            ]
        }
    
    async def get_permissions_summary(self, user_id: str) -> Dict[str, Any]:
        """Get user permissions summary grouped by resource"""
        user_perms_data = await self.get_user_permissions(user_id)
        permissions = user_perms_data.get('permissions', [])
        
        # Group permissions by resource
        permissions_by_resource = {}
        for perm in permissions:
            resource = perm.get('resource', 'unknown')
            if resource not in permissions_by_resource:
                permissions_by_resource[resource] = {
                    'resource': resource,
                    'permissions': [],
                    'actions': []
                }
            permissions_by_resource[resource]['permissions'].append(perm)
            permissions_by_resource[resource]['actions'].append(perm.get('action', 'unknown'))
        
        # Convert to list and sort
        summary = list(permissions_by_resource.values())
        summary.sort(key=lambda x: x['resource'])
        
        return {
            "user_id": user_id,
            "user_name": user_perms_data.get('user_name'),
            "role": user_perms_data.get('role'),
            "total_permissions": len(permissions),
            "resources_count": len(summary),
            "permissions_by_resource": summary
        }
    
    async def get_role_permissions_summary(self, role_id: str) -> Dict[str, Any]:
        """Get role permissions summary grouped by resource"""
        role_perms_data = await self.get_role_permissions(role_id)
        if not role_perms_data:
            return None
        
        permissions = role_perms_data.get('permissions', [])
        
        # Group permissions by resource
        permissions_by_resource = {}
        for perm in permissions:
            resource = perm.get('resource', 'unknown')
            if resource not in permissions_by_resource:
                permissions_by_resource[resource] = {
                    'resource': resource,
                    'permissions': [],
                    'actions': []
                }
            permissions_by_resource[resource]['permissions'].append(perm)
            permissions_by_resource[resource]['actions'].append(perm.get('action', 'unknown'))
        
        # Convert to list and sort
        summary = list(permissions_by_resource.values())
        summary.sort(key=lambda x: x['resource'])
        
        return {
            "role_id": role_id,
            "role_name": role_perms_data.get('role_name'),
            "role_description": role_perms_data.get('role_description'),
            "total_permissions": len(permissions),
            "resources_count": len(summary),
            "users_with_role": role_perms_data.get('users_with_role'),
            "permissions_by_resource": summary
        }


# Singleton instance
_permission_service = None

def get_permission_service() -> PermissionService:
    """Get permission service singleton"""
    global _permission_service
    if _permission_service is None:
        _permission_service = PermissionService()
    return _permission_service