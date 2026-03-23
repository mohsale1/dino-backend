from typing import List, Dict, Any
from src.repositories.PermissionRepository import PermissionRepository
from src.repositories.RoleRepository import RoleRepository


class ApplicationPermissionService:
    def __init__(self):
        self.permission_repo = PermissionRepository()
        self.role_repo = RoleRepository()

    def get_permissions_for_user(self, user: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get full permission objects for the current user based on their role."""
        role = user.get('role', {})
        if isinstance(role, str):
            return []

        permission_ids: List[str] = role.get('permissions', [])
        if not permission_ids:
            return []

        permissions = []
        for perm_id in permission_ids:
            perm = self.permission_repo.get_by_id(perm_id)
            if perm:
                permissions.append({
                    'id': perm.get('id'),
                    'name': perm.get('name'),
                    'resource': perm.get('resource'),
                    'action': perm.get('action'),
                    'description': perm.get('description'),
                    'category': perm.get('category'),
                })
        return permissions

    def get_role_info(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Get role info for the current user."""
        role = user.get('role', {})
        if isinstance(role, str):
            return {'name': role}
        return {
            'id': role.get('id'),
            'name': role.get('name'),
            'description': role.get('description'),
        }
