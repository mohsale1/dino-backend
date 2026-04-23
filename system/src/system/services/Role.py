"""
RoleService — manages roles and their permission associations.
"""

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

    async def create_role(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a role and return the created dict."""
        return await self.create(data)

    async def get_all_roles(self) -> List[Dict[str, Any]]:
        return await self.get_all()

    async def get_role_by_id(
        self, role_id: int, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        return await self.get_by_id(role_id, include_deleted)

    async def get_roles_by_type(self, role_type: int) -> List[Dict[str, Any]]:
        return await self.role_repo.get_by_type(role_type)

    async def update_role(self, role_id: int, data: Dict[str, Any]) -> bool:
        return await self.update(role_id, data)

    async def soft_delete_role(self, role_id: int) -> bool:
        return await self.soft_delete(role_id)

    async def restore_role(self, role_id: int) -> bool:
        return await self.restore(role_id)

    # ------------------------------------------------------------------
    # Existence / validation
    # ------------------------------------------------------------------

    async def role_exists(self, name: str, role_type: int) -> bool:
        return await self.role_repo.get_by_name_and_type(name, role_type) is not None

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    async def add_permissions(self, role_id: int, permission_ids: List[int]) -> bool:
        return await self.role_repo.add_permissions(role_id, permission_ids)

    async def remove_permissions(self, role_id: int, permission_ids: List[int]) -> bool:
        return await self.role_repo.remove_permissions(role_id, permission_ids)

    async def get_role_permissions(self, role_id: int) -> List[int]:
        return await self.role_repo.get_role_permissions(role_id)

    # ------------------------------------------------------------------
    # User queries
    # ------------------------------------------------------------------

    async def is_role_in_use(self, role_id: int) -> bool:
        """Return True if any user is assigned this role."""
        user_repo = UserRepository(self.db)
        users = await user_repo.get_by_role(role_id)
        return bool(users)

    async def get_users_by_role(self, role_id: int) -> List[Dict[str, Any]]:
        """Return all users with this role, password_hash stripped."""
        user_repo = UserRepository(self.db)
        users = await user_repo.get_by_role(role_id)
        for u in users:
            u.pop("password_hash", None)
        return users
