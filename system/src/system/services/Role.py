from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository


class RoleService(BaseService):
    """Service for managing roles."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.role_repo = RoleRepository(db)
        super().__init__(self.role_repo)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_role(self, data: Dict[str, Any]) -> str:
        """Create a role and return its ID string."""
        result = await self.create(data)
        return result.get('id') if isinstance(result, dict) else result

    async def get_all_roles(self) -> List[Dict[str, Any]]:
        return await self.get_all()

    async def get_role_by_id(self, role_id, include_deleted: bool = False):
        return await self.get_by_id(role_id, include_deleted)

    async def get_roles_by_type(self, role_type) -> List[Dict[str, Any]]:
        return await self.role_repo.get_by_type(role_type)

    async def update_role(self, role_id, data: Dict[str, Any]):
        return await self.update(role_id, data)

    async def soft_delete_role(self, role_id):
        return await self.soft_delete(role_id)

    async def restore_role(self, role_id):
        return await self.restore(role_id)

    # ------------------------------------------------------------------
    # Existence / validation
    # ------------------------------------------------------------------

    async def role_exists(self, name: str, role_type) -> bool:
        return await self.role_repo.get_by_name_and_type(name, role_type) is not None

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    async def add_permissions(self, role_id, permission_ids: List) -> Any:
        return await self.role_repo.add_permissions(role_id, permission_ids)

    async def remove_permissions(self, role_id, permission_ids: List) -> Any:
        return await self.role_repo.remove_permissions(role_id, permission_ids)

    async def get_role_permissions(self, role_id) -> List[Dict[str, Any]]:
        return await self.role_repo.get_role_permissions(role_id)

    # ------------------------------------------------------------------
    # User queries
    # ------------------------------------------------------------------

    async def is_role_in_use(self, role_id) -> bool:
        user_repo = UserRepository(self.db)
        users = await user_repo.get_by_role(role_id)
        return bool(users)

    async def get_users_by_role(self, role_id) -> List[Dict[str, Any]]:
        user_repo = UserRepository(self.db)
        return await user_repo.get_by_role(role_id)

    # ------------------------------------------------------------------
    # Static helpers (no DB access)
    # ------------------------------------------------------------------

    def get_default_permissions_for_role(self, role_name: str) -> List[str]:
        """Return the default permission list for a named role (static data)."""
        defaults: Dict[str, List[str]] = {
            "SuperAdmin": ["system:*"],
            "BillingManager": ["system:billing:*", "system:workspaces:read"],
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
                "persona:read",
                "workspace:read",
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
                "persona:read",
                "workspace:read",
            ],
        }
        return defaults.get(role_name, [])
