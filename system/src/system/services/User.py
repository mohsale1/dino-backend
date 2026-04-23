"""
SystemUserService — manages system users (user_type=0) in the unified users table.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.core.Security import get_password_hash
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository


class SystemUserService(BaseService):
    """Service for managing system users (user_type=0)."""

    def __init__(self, db: AsyncSession) -> None:
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        super().__init__(self.user_repo)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Hash password, enforce user_type=0, create in users table."""
        if "password" in data:
            data["password_hash"] = get_password_hash(data.pop("password"))
        data["user_type"] = 0
        data.setdefault("is_active", True)
        data.setdefault("workspace_id", None)
        return await self.user_repo.create(data)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, user_id: int, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Fetch a user by ID."""
        return await self.user_repo.get_by_id(user_id, include_deleted=include_deleted)

    async def get_user_with_role(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch user enriched with role information, password_hash stripped."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        if user.get("role_id"):
            role = await self.role_repo.get_by_id(user["role_id"])
            if role:
                user["role"] = {
                    "id": role["id"],
                    "name": role["name"],
                    "role_type": role.get("role_type", 0),
                }
        user.pop("password_hash", None)
        return user

    async def get_paginated_users(
        self,
        user_type: Optional[int] = None,
        workspace_id: Optional[int] = None,
        role_id: Optional[int] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated users with role enrichment, password_hash stripped."""
        items, total, total_pages = await self.user_repo.get_paginated_users(
            user_type=user_type,
            workspace_id=workspace_id,
            role_id=role_id,
            search_query=search,
            page=page,
            page_size=page_size,
            include_deleted=include_deleted,
        )
        sanitized: List[Dict[str, Any]] = []
        for user in items:
            u = dict(user)
            u.pop("password_hash", None)
            if u.get("role_id"):
                role = await self.role_repo.get_by_id(u["role_id"])
                if role:
                    u["role"] = {"id": role["id"], "name": role["name"]}
            sanitized.append(u)
        return sanitized, total, total_pages

    async def email_exists(
        self,
        email: str,
        workspace_id: Optional[int] = None,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Check email uniqueness."""
        return await self.user_repo.email_exists(email, workspace_id, exclude_id)

    async def get_users_by_role(self, role_id: int) -> List[Dict[str, Any]]:
        """Return all users with the given role."""
        users = await self.user_repo.get_by_role(role_id)
        for u in users:
            u.pop("password_hash", None)
        return users

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """Update user; hash password if present."""
        if "password" in data:
            data["password_hash"] = get_password_hash(data.pop("password"))
        return await self.update(user_id, data)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_user(self, user_id: int) -> bool:
        """Soft delete: set is_active=False."""
        return await self.update(user_id, {"is_active": False})

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_system_role(self, role_id: int) -> bool:
        """Return True if the role exists and is a system role (role_type=0)."""
        role = await self.role_repo.get_by_id(role_id)
        return role.get("role_type") == 0 if role else False
