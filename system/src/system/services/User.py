from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.core.Security import get_password_hash
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository


class SystemUserService(BaseService):
    """
    Service for managing system users.

    Deletion strategy: no soft-delete columns on system_users.
    Deleting a user sets is_active = False. The record is never hidden.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        super().__init__(self.user_repo)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_system_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        if "password" in user_data:
            user_data["password_hash"] = get_password_hash(user_data.pop("password"))
        user_data["is_active"] = user_data.get("is_active", True)
        return await self.user_repo.create(user_data)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a user by ID regardless of active status."""
        return await self.user_repo.get_by_id(user_id, include_deleted=True)

    async def get_user_with_role(self, user_id: str) -> Optional[Dict[str, Any]]:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        if user.get("role_id"):
            role = await self.role_repo.get_by_id(user["role_id"])
            if role:
                user["role"] = {
                    "id": str(role["id"]),
                    "name": role["name"],
                    "role_type": role.get("role_type", 0),
                }
        user.pop("password_hash", None)
        return user

    async def get_paginated_users(
        self,
        page: int = 1,
        page_size: int = 10,
        role_id: Optional[str] = None,
        search_query: Optional[str] = None,
        active_only: bool = True,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        items, total, total_pages = await self.user_repo.get_paginated_users(
            role_id=role_id,
            search_query=search_query,
            active_only=active_only,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_direction=order_direction,
        )
        sanitized: List[Dict[str, Any]] = []
        for user in items:
            u = dict(user)
            u.pop("password_hash", None)
            if u.get("role_id"):
                role = await self.role_repo.get_by_id(u["role_id"])
                if role:
                    u["role"] = {"id": str(role["id"]), "name": role["name"]}
            sanitized.append(u)
        return sanitized, total, total_pages

    async def email_exists(self, email: str) -> bool:
        return await self.user_repo.email_exists(email)

    async def get_users_by_role(self, role_id: str) -> List[Dict[str, Any]]:
        return await self.user_repo.get_by_role(role_id)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_user(self, user_id: str, data: Dict[str, Any]) -> bool:
        if "password" in data:
            data["password_hash"] = get_password_hash(data.pop("password"))
        return await self.update(user_id, data)

    # ------------------------------------------------------------------
    # Delete — sets is_active = False (no soft-delete columns)
    # ------------------------------------------------------------------

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a system user by setting is_active = False.
        The record is retained in the database permanently.
        """
        return await self.update(user_id, {"is_active": False})

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_system_role(self, role_id: str) -> bool:
        role = await self.role_repo.get_by_id(role_id)
        return role.get("role_type") == 0 if role else False
