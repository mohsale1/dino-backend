"""
UserRepository — unified users table, application-side.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.User import User, user_personas


class UserRepository(BaseRepository):
    """Repository for application users (user_type=1) in the unified users table."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(User, db)

    async def get_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """Return all active application users (user_type=1) belonging to a workspace."""
        stmt = (
            select(User)
            .where(
                User.workspace_id == workspace_id,
                User.user_type == 1,
                User.is_active.is_(True),
            )
            .order_by(User.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return [row_to_dict(r) for r in result.scalars().all()]

    async def get_by_persona(self, persona_id: int) -> List[Dict[str, Any]]:
        """Return all active users linked to a persona via user_personas."""
        stmt = (
            select(User)
            .join(user_personas, user_personas.c.user_id == User.id)
            .where(
                user_personas.c.persona_id == persona_id,
                User.is_active.is_(True),  # noqa: E712
            )
        )
        result = await self.db.execute(stmt)
        return [row_to_dict(r) for r in result.scalars().all()]

    async def get_by_role(self, role_id: int) -> List[Dict[str, Any]]:
        """Return all active application users (user_type=1) assigned to a role."""
        stmt = (
            select(User)
            .where(
                User.role_id == role_id,
                User.user_type == 1,
                User.is_active.is_(True),
            )
            .order_by(User.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return [row_to_dict(r) for r in result.scalars().all()]

    async def email_exists(
        self,
        email: str,
        workspace_id: int,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Return True if a user with this email exists in the workspace."""
        clauses = [
            User.email == email.lower(),
            User.workspace_id == workspace_id,
        ]
        if exclude_id is not None:
            clauses.append(User.id != exclude_id)
        stmt = select(func.count()).select_from(User).where(and_(*clauses))
        count = (await self.db.execute(stmt)).scalar_one()
        return count > 0

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
        """Return (items, total_count, total_pages) with optional filters."""
        clauses = []

        if not include_deleted:
            clauses.append(User.is_active.is_(True))  # noqa: E712

        clauses.append(User.user_type == 1)

        if workspace_id is not None:
            clauses.append(User.workspace_id == workspace_id)

        if role_id is not None:
            clauses.append(User.role_id == role_id)

        if search_query:
            q = search_query.strip()
            clauses.append(
                or_(
                    User.email.ilike(f"%{q}%"),
                    User.first_name.ilike(f"%{q}%"),
                    User.last_name.ilike(f"%{q}%"),
                )
            )

        # persona_id filter via join
        if persona_id is not None:
            stmt_base = (
                select(User)
                .join(user_personas, user_personas.c.user_id == User.id)
                .where(user_personas.c.persona_id == persona_id)
            )
            if clauses:
                stmt_base = stmt_base.where(and_(*clauses))

            count_stmt = select(func.count()).select_from(
                stmt_base.subquery()
            )
            total = (await self.db.execute(count_stmt)).scalar_one() or 0
            total_pages = max(1, (total + page_size - 1) // page_size)

            data_stmt = stmt_base.order_by(User.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
            rows = (await self.db.execute(data_stmt)).scalars().all()
            return [row_to_dict(r) for r in rows], total, total_pages

        where_expr = and_(*clauses) if clauses else None

        count_stmt = select(func.count()).select_from(User)
        if where_expr is not None:
            count_stmt = count_stmt.where(where_expr)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        data_stmt = select(User)
        if where_expr is not None:
            data_stmt = data_stmt.where(where_expr)
        data_stmt = data_stmt.order_by(User.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages
