"""
ApplicationUserService — manages application users (user_type=1).
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.core.Security import get_password_hash
from src.models.Role import Role
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository


class ApplicationUserService:
    """Service for managing application users."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new application user."""
        if "password" in user_data:
            user_data["password_hash"] = get_password_hash(user_data.pop("password"))
        user_data["user_type"] = 1
        user_data.setdefault("is_active", True)
        result = await self.user_repo.create(user_data)
        result.pop("password_hash", None)
        return result

    async def get_by_id(
        self, user_id: int, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        return await self.user_repo.get_by_id(user_id, include_deleted)

    async def get_user_with_role(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user with role resolved, password_hash stripped."""
        user = await self.get_by_id(user_id, include_deleted=False)
        if not user:
            return None
        users = await self._enrich_and_sanitize([user])
        return users[0] if users else None

    async def get_paginated_users(
        self,
        workspace_id: Optional[int] = None,
        persona_id: Optional[int] = None,
        role_id: Optional[int] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated users with role enrichment."""
        items, total, total_pages = await self.user_repo.get_paginated_users(
            workspace_id=workspace_id,
            persona_id=persona_id,
            role_id=role_id,
            search_query=search_query,
            page=page,
            page_size=page_size,
            include_deleted=include_deleted,
        )
        return await self._enrich_and_sanitize(items), total, total_pages

    async def _enrich_and_sanitize(
        self, users: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Resolve role_id -> role object and strip sensitive fields."""
        sanitized: List[Dict[str, Any]] = []
        role_ids: set = set()
        for user in users:
            user = {k: v for k, v in user.items() if k != "password_hash"}
            sanitized.append(user)
            role_id = user.get("role_id")
            if role_id is not None and role_id not in role_ids:
                role_ids.add(role_id)

        role_cache: Dict[int, Dict[str, Any]] = {}
        if role_ids:
            stmt = select(Role).where(Role.id.in_(role_ids))
            result = await self.db.execute(stmt)
            for row in result.scalars().all():
                d = row_to_dict(row)
                role_cache[d["id"]] = d

        result_list = []
        for user in sanitized:
            role_id = user.get("role_id")
            if role_id is not None:
                role = role_cache.get(role_id)
                if role:
                    user["role"] = {
                        "id": role.get("id"),
                        "name": role.get("name"),
                        "role_type": role.get("role_type", 1),
                    }
            result_list.append(user)

        return result_list


    async def update_user(
        self,
        user_id: int,
        data: Dict[str, Any],
        workspace_id: Optional[int] = None,
    ) -> bool:
        """Update user, hashing password if present. Optionally scope to workspace."""
        if workspace_id is not None:
            existing = await self.user_repo.get_by_id(user_id)
            if not existing or existing.get("workspace_id") != workspace_id:
                return False
        if "password" in data:
            data["password_hash"] = get_password_hash(data.pop("password"))
        return await self.user_repo.update(user_id, data)


    async def soft_delete_user(self, user_id: int) -> bool:
        return await self.user_repo.soft_delete(user_id)

    async def restore_user(self, user_id: int) -> bool:
        return await self.user_repo.restore(user_id)

    async def email_exists(
        self, email: str, workspace_id: int, exclude_id: Optional[int] = None
    ) -> bool:
        return await self.user_repo.email_exists(email, workspace_id, exclude_id)

    async def validate_application_role(self, role_id: int) -> bool:
        """Return True if the role exists and is an application role (role_type=1)."""
        role = await self.role_repo.get_by_id(role_id)
        return role.get("role_type") == 1 if role else False

    async def get_users_by_role(
        self, role_id: int, workspace_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        filters: Dict[str, Any] = {"role_id": role_id}
        if workspace_id:
            filters["workspace_id"] = workspace_id
        items = await self.user_repo.get_all(filters=filters)
        return await self._enrich_and_sanitize(items)

    async def get_users_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        items = await self.user_repo.get_by_workspace(workspace_id)
        return await self._enrich_and_sanitize(items)
