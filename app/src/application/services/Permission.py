from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.PermissionRepository import PermissionRepository
from src.repositories.RoleRepository import RoleRepository


class ApplicationPermissionService:
    """Permission service — async SQLAlchemy 2.x."""

    def __init__(self, db: AsyncSession) -> None:
        self.permission_repo = PermissionRepository(db)
        self.role_repo = RoleRepository(db)

    async def get_permissions_for_user(self, user: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get full permission objects for the current user based on their role."""
        role = user.get("role", {})
        if isinstance(role, str):
            return []

        permission_ids: List[str] = role.get("permissions", [])
        if not permission_ids:
            return []

        permissions: List[Dict[str, Any]] = []
        for perm_id in permission_ids:
            perm = await self.permission_repo.get_by_id(perm_id)
            if perm:
                permissions.append(
                    {
                        "id": perm.get("id"),
                        "name": perm.get("name"),
                        "resource": perm.get("resource"),
                        "action": perm.get("action"),
                        "description": perm.get("description"),
                        "category": perm.get("category"),
                    }
                )
        return permissions

    def get_role_info(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Get role info for the current user (synchronous — no DB access)."""
        role = user.get("role", {})
        if isinstance(role, str):
            return {"name": role}
        return {
            "id": role.get("id"),
            "name": role.get("name"),
            "description": role.get("description"),
        }
