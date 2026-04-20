"""
Application User Service
Handles business logic for application user management
"""
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.UserRepository import UserRepository
from src.repositories.RoleRepository import RoleRepository
from src.core.Security import get_password_hash


class ApplicationUserService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    async def create_application_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new application user and return the new user's ID as a string."""
        if 'password' in user_data:
            user_data['password_hash'] = get_password_hash(user_data.pop('password'))

        user_data['is_active'] = user_data.get('is_active', True)

        result = await self.user_repo.create(user_data)
        return str(result.get('id'))

    async def get_paginated_users(
        self,
        page: int = 1,
        page_size: int = 10,
        workspace_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        role_id: Optional[str] = None,
        search_query: Optional[str] = None,
        include_deleted: bool = False,
        order_by: str = 'created_at',
        order_direction: str = 'desc'
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated list of application users with role resolved and sensitive fields stripped"""
        items, total, total_pages = await self.user_repo.get_paginated_users(
            workspace_id=workspace_id,
            persona_id=persona_id,
            role_id=role_id,
            search_query=search_query,
            page=page,
            page_size=page_size,
            include_deleted=include_deleted,
            order_by=order_by,
            order_direction=order_direction
        )
        return await self._enrich_and_sanitize(items), total, total_pages

    async def get_by_id(self, user_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        return await self.user_repo.get_by_id(user_id, include_deleted)

    async def get_user_with_role(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a single user with role resolved and sensitive fields stripped"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        users = await self._enrich_and_sanitize([user])
        return users[0] if users else None

    async def _enrich_and_sanitize(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve role_id -> role object and strip sensitive fields for a list of users.

        Collects all unique role IDs first, then issues a single WHERE id IN (...)
        query instead of one query per user, reducing DB round-trips from O(N) to O(1).
        """
        from sqlalchemy import select
        from src.models.Role import Role
        from src.base.BaseModel import row_to_dict

        # Sanitize all users and collect unique role IDs in one pass.
        sanitized: List[Dict[str, Any]] = []
        role_ids: List[str] = []
        for user in users:
            user = self._sanitize_user(user)
            sanitized.append(user)
            role_id = user.get('role_id')
            if role_id and role_id not in role_ids:
                role_ids.append(role_id)

        # Batch-fetch all required roles in a single query.
        role_cache: Dict[str, Dict[str, Any]] = {}
        if role_ids:
            stmt = select(Role).where(Role.id.in_(role_ids))
            result = await self.role_repo.db.execute(stmt)
            for row in result.scalars().all():
                d = row_to_dict(row)
                role_cache[str(d['id'])] = d

        result_list = []
        for user in sanitized:
            role_id = user.pop('role_id', None)
            if role_id:
                role = role_cache.get(str(role_id))
                if role:
                    user['role'] = {
                        'id': role.get('id'),
                        'name': role.get('name'),
                        'role_type': role.get('role_type', 1)
                    }
            result_list.append(user)

        return result_list


    def _sanitize_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Strip sensitive fields from a user record"""
        sensitive = {'password_hash', 'password', 'reset_token', 'reset_token_expires_at'}
        return {k: v for k, v in user.items() if k not in sensitive}

    async def update_user(
        self,
        user_id: str,
        data: Dict[str, Any],
        workspace_id: Optional[str] = None
    ) -> bool:
        """Update user, hashing password if present.

        When workspace_id is provided the update is scoped to that workspace —
        users belonging to a different workspace are silently rejected (returns
        False) so callers cannot mutate records outside their own tenant.
        """
        if workspace_id:
            existing = await self.user_repo.get_by_id(user_id)
            if not existing or str(existing.get('workspace_id')) != str(workspace_id):
                return False

        if 'password' in data:
            data['password_hash'] = get_password_hash(data.pop('password'))

        return await self.user_repo.update(user_id, data)


    async def soft_delete_user(self, user_id: str) -> bool:
        """Soft delete user"""
        return await self.user_repo.soft_delete(user_id)

    async def restore_user(self, user_id: str) -> bool:
        """Restore soft-deleted user"""
        return await self.user_repo.restore(user_id)

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists"""
        return await self.user_repo.email_exists(email)

    async def validate_application_role(self, role_id: str) -> bool:
        """Validate that role exists and is an application role (role_type = 1)"""
        role = await self.role_repo.get_by_id(role_id)
        return role.get('role_type') == 1 if role else False

    async def get_users_by_role(
        self,
        role_id: str,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all users with a specific role, scoped to a workspace at the DB level."""
        filters: Dict[str, Any] = {'role_id': role_id}
        if workspace_id:
            filters['workspace_id'] = workspace_id
        items = await self.user_repo.get_all(filters=filters)
        return await self._enrich_and_sanitize(items)


    async def get_users_by_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get all users in a workspace"""
        items = await self.user_repo.get_by_workspace(workspace_id)
        return await self._enrich_and_sanitize(items)

    async def get_users_by_persona(
        self,
        persona_id: str,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all users in a persona, scoped to a workspace at the DB level."""
        filters: Dict[str, Any] = {'persona_id': persona_id}
        if workspace_id:
            filters['workspace_id'] = workspace_id
        items = await self.user_repo.get_all(filters=filters)
        return await self._enrich_and_sanitize(items)

