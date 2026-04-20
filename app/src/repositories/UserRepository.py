"""
UserRepository — application_users only.

Handles CRUD and query operations for ApplicationUser records.
System users (dino-system service) are NOT managed here.
"""

from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.User import ApplicationUser


class UserRepository(BaseRepository):
    """Repository for application-level workspace users."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(ApplicationUser, db)

    # ------------------------------------------------------------------
    # Scoped list queries
    # ------------------------------------------------------------------

    async def get_by_workspace(
        self,
        workspace_id,
        include_deleted: bool = False,
    ) -> List[dict]:
        """Return all users belonging to a workspace."""
        return await self.get_all(
            filters={"workspace_id": workspace_id},
            include_deleted=include_deleted,
        )

    async def get_by_persona(
        self,
        persona_id,
        include_deleted: bool = False,
    ) -> List[dict]:
        """Return all users belonging to a persona."""
        return await self.get_all(
            filters={"persona_id": persona_id},
            include_deleted=include_deleted,
        )

    async def get_by_role(
        self,
        role_id,
        include_deleted: bool = False,
    ) -> List[dict]:
        """Return all users assigned to a role."""
        return await self.get_all(
            filters={"role_id": role_id},
            include_deleted=include_deleted,
        )

    # ------------------------------------------------------------------
    # Paginated / filtered query
    # ------------------------------------------------------------------

    async def get_paginated_users(
        self,
        workspace_id=None,
        persona_id=None,
        role_id=None,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        include_deleted: bool = False,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[dict], int, int]:
        """
        Paginated user listing with optional filters and full-text search.

        Returns
        -------
        (items, total_count, total_pages)
        """
        clauses = []

        if not include_deleted:
            clauses.append(ApplicationUser.is_active == True)  # noqa: E712

        if workspace_id is not None:
            clauses.append(ApplicationUser.workspace_id == workspace_id)

        if persona_id is not None:
            clauses.append(ApplicationUser.persona_id == persona_id)

        if role_id is not None:
            clauses.append(ApplicationUser.role_id == role_id)

        if search_query:
            q = search_query.strip()
            clauses.append(
                or_(
                    ApplicationUser.email.ilike(f"%{q}%"),
                    ApplicationUser.first_name.ilike(f"%{q}%"),
                    ApplicationUser.last_name.ilike(f"%{q}%"),
                )
            )

        where_expr = and_(*clauses) if clauses else None

        # COUNT query
        count_stmt = select(func.count()).select_from(ApplicationUser)
        if where_expr is not None:
            count_stmt = count_stmt.where(where_expr)
        total_count: int = (await self.db.execute(count_stmt)).scalar_one()

        total_pages = max(1, (total_count + page_size - 1) // page_size)

        # DATA query
        data_stmt = select(ApplicationUser)
        if where_expr is not None:
            data_stmt = data_stmt.where(where_expr)

        order_expr = self._order_column(order_by, order_direction)
        if order_expr is not None:
            data_stmt = data_stmt.order_by(order_expr)

        data_stmt = data_stmt.limit(page_size).offset((page - 1) * page_size)
        result = await self.db.execute(data_stmt)
        items = [row_to_dict(row) for row in result.scalars().all()]

        return items, total_count, total_pages

    # ------------------------------------------------------------------
    # Existence check
    # ------------------------------------------------------------------

    async def email_exists(
        self,
        email: str,
        exclude_id=None,
    ) -> bool:
        """
        Return True when an active user with the given email already exists.
        Pass *exclude_id* to allow the current user's own email through (update flow).
        """
        clauses = [
            ApplicationUser.email == email.lower(),
            ApplicationUser.is_active == True,  # noqa: E712
        ]

        if exclude_id is not None:
            clauses.append(ApplicationUser.id != exclude_id)

        stmt = (
            select(func.count())
            .select_from(ApplicationUser)
            .where(and_(*clauses))
        )
        count: int = (await self.db.execute(stmt)).scalar_one()
        return count > 0
