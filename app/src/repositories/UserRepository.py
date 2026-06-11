"""
UserRepository — unified users table, application-side.
workspace_id removed — workspace scoping via user_personas join.
email is globally unique.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.User import User, user_personas
from src.models.Workspace import workspace_personas


class UserRepository(BaseRepository):
    """Repository for application users (user_type=1) in the unified users table."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(User, db)

    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active app users linked to a workspace via user_personas → workspace_personas."""
        stmt = (
            select(User)
            .join(user_personas, user_personas.c.user_id == User.id)
            .join(workspace_personas, workspace_personas.c.persona_id == user_personas.c.persona_id)
            .where(
                workspace_personas.c.workspace_id == workspace_id,
                User.user_type == 1,
                User.is_active.is_(True),
            )
            .distinct()
            .order_by(User.created_at.desc())
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [row_to_dict(r) for r in rows]

    async def get_by_persona(self, persona_id: int) -> List[Dict[str, Any]]:
        """Return all active users linked to a persona via user_personas."""
        stmt = (
            select(User)
            .join(user_personas, user_personas.c.user_id == User.id)
            .where(
                user_personas.c.persona_id == persona_id,
                User.is_active.is_(True),
            )
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [row_to_dict(r) for r in rows]

    async def get_by_role(self, role_id: int) -> List[Dict[str, Any]]:
        """Return all active application users (user_type=1) assigned to a role."""
        stmt = (
            select(User)
            .where(User.role_id == role_id, User.user_type == 1, User.is_active.is_(True))
            .order_by(User.created_at.desc())
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [row_to_dict(r) for r in rows]

    async def email_exists(
        self,
        email: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Return True if an application user (user_type=1) with this email already exists."""
        clauses = [User.email == email.lower(), User.user_type == 1]
        if exclude_id is not None:
            clauses.append(User.id != exclude_id)
        stmt = select(func.count()).select_from(User).where(and_(*clauses))
        return (await self.db.execute(stmt)).scalar_one() > 0


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
        """Return paginated app users. Workspace scoping via user_personas join."""
        clauses = [User.user_type == 1]
        if not include_deleted:
            clauses.append(User.is_active.is_(True))
        if role_id is not None:
            clauses.append(User.role_id == role_id)
        if search_query:
            q = search_query.strip()
            clauses.append(or_(
                User.email.ilike(f"%{q}%"),
                User.first_name.ilike(f"%{q}%"),
                User.last_name.ilike(f"%{q}%"),
            ))

        # Build base — join through user_personas when workspace or persona filter needed
        if workspace_id is not None or persona_id is not None:
            base = (
                select(User)
                .join(user_personas, user_personas.c.user_id == User.id)
            )
            if workspace_id is not None:
                base = base.join(
                    workspace_personas,
                    workspace_personas.c.persona_id == user_personas.c.persona_id,
                ).where(workspace_personas.c.workspace_id == workspace_id)
            if persona_id is not None:
                base = base.where(user_personas.c.persona_id == persona_id)
            base = base.where(and_(*clauses)).distinct()
        else:
            base = select(User).where(and_(*clauses))

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        data_stmt = (
            base.order_by(User.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages
