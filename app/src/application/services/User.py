"""
ApplicationUserService — manages application users (user_type=1).
workspace_id removed from users table — scoped via user_personas.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.core.Security import get_password_hash
from src.models.Role import Role
from src.models.User import user_personas
from src.repositories.PersonaRepository import PersonaRepository
from src.repositories.RoleRepository import RoleRepository
from src.repositories.UserRepository import UserRepository

logger = logging.getLogger(__name__)


class ApplicationUserService:
    """Service for managing application users."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new application user and optionally link to personas (bulk insert)."""
        persona_ids: Optional[List[int]] = user_data.pop("persona_ids", None)

        if "password" in user_data:
            user_data["password_hash"] = get_password_hash(user_data.pop("password"))
        user_data["user_type"] = 1
        user_data.setdefault("is_active", True)

        result = await self.user_repo.create(user_data)
        user_id = result["id"]

        # Bulk insert persona links — single execute instead of N loops
        if persona_ids:
            await self.db.execute(
                pg_insert(user_personas)
                .values([{"user_id": user_id, "persona_id": pid} for pid in persona_ids])
                .on_conflict_do_nothing()
            )

        result.pop("password_hash", None)
        result["persona_ids"] = persona_ids or []
        logger.info(
            "user.created user_id=%s role_id=%s persona_ids=%s",
            user_id, result.get("role_id"), persona_ids,
        )
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

    async def get_user_with_personas(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user with role + all linked personas.
        Single query for personas via IN clause — no N+1.
        """
        user = await self.get_user_with_role(user_id)
        if not user:
            return None

        # Fetch all persona_ids for this user in one query
        persona_id_rows = (
            await self.db.execute(
                select(user_personas.c.persona_id).where(
                    user_personas.c.user_id == user_id
                )
            )
        ).all()
        persona_ids = [r[0] for r in persona_id_rows]

        personas: List[Dict[str, Any]] = []
        if persona_ids:
            persona_repo = PersonaRepository(self.db)
            # Fetch all personas in one query using get_all with in-clause
            from sqlalchemy import select as sa_select
            from src.models.Persona import Persona
            from src.base.BaseModel import row_to_dict as _rtd
            stmt = sa_select(Persona).where(
                Persona.id.in_(persona_ids),
                Persona.is_active.is_(True),
            )
            rows = (await self.db.execute(stmt)).scalars().all()
            personas = [_rtd(r) for r in rows]

        return {"user": user, "personas": personas}

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
        """Return paginated users with role enrichment and index field."""
        items, total, total_pages = await self.user_repo.get_paginated_users(
            workspace_id=workspace_id,
            persona_id=persona_id,
            role_id=role_id,
            search_query=search_query,
            page=page,
            page_size=page_size,
            include_deleted=include_deleted,
        )
        offset = (page - 1) * page_size
        enriched = await self._enrich_and_sanitize(items)
        for idx, user in enumerate(enriched, start=offset + 1):
            user["index"] = idx
        return enriched, total, total_pages

    async def _enrich_and_sanitize(
        self, users: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Resolve role_id → role object and strip sensitive fields.
        Fetches all unique roles in a single IN query.
        """
        sanitized: List[Dict[str, Any]] = []
        role_ids: set = set()
        for user in users:
            user = {k: v for k, v in user.items() if k != "password_hash"}
            sanitized.append(user)
            if user.get("role_id") is not None:
                role_ids.add(user["role_id"])

        role_cache: Dict[int, Dict[str, Any]] = {}
        if role_ids:
            stmt = select(Role).where(Role.id.in_(role_ids))
            for row in (await self.db.execute(stmt)).scalars().all():
                d = row_to_dict(row)
                role_cache[d["id"]] = d

        for user in sanitized:
            role_id = user.get("role_id")
            if role_id is not None:
                role = role_cache.get(role_id)
                if role:
                    user["role"] = {
                        "id": role["id"],
                        "name": role["name"],
                        "role_type": role.get("role_type", 1),
                    }

        return sanitized

    async def update_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """Update user, hashing password if present."""
        if "password" in data:
            data["password_hash"] = get_password_hash(data.pop("password"))
        updated = await self.user_repo.update(user_id, data)
        if updated:
            logger.info("user.updated user_id=%s fields=%s", user_id, list(data.keys()))
        return updated

    async def soft_delete_user(self, user_id: int) -> bool:
        deleted = await self.user_repo.soft_delete(user_id)
        if deleted:
            logger.info("user.deleted user_id=%s", user_id)
        return deleted

    async def restore_user(self, user_id: int) -> bool:
        restored = await self.user_repo.restore(user_id)
        if restored:
            logger.info("user.restored user_id=%s", user_id)
        return restored

    async def email_exists(
        self, email: str, exclude_id: Optional[int] = None
    ) -> bool:
        return await self.user_repo.email_exists(email, exclude_id)

    async def validate_application_role(self, role_id: int) -> bool:
        """Return True if the role exists and is an application role (role_type=1)."""
        role = await self.role_repo.get_by_id(role_id)
        return role.get("role_type") == 1 if role else False

    async def get_users_by_role(
        self, role_id: int, workspace_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        items, _, _ = await self.user_repo.get_paginated_users(
            role_id=role_id, workspace_id=workspace_id
        )
        return await self._enrich_and_sanitize(items)

    async def get_users_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        items = await self.user_repo.get_by_workspace(workspace_id)
        return await self._enrich_and_sanitize(items)
