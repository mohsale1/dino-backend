"""
UserRepository — async SQLAlchemy 2.x repository for the unified User model.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.User import User


class UserRepository(BaseRepository):
    """Repository for User entities (both system and application users)."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(User, db)

    # ------------------------------------------------------------------
    # Simple lookups
    # ------------------------------------------------------------------

    async def get_by_role(self, role_id: int) -> List[Dict[str, Any]]:
        """Return all active users assigned to the given role."""
        return await self.get_all(filters={"role_id": role_id})

    async def get_by_user_type(self, user_type: int) -> List[Dict[str, Any]]:
        """Return all active users of the given type (0=System, 1=Application)."""
        return await self.get_all(filters={"user_type": user_type})

    # ------------------------------------------------------------------
    # Existence check
    # ------------------------------------------------------------------

    async def email_exists(
        self,
        email: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """Return True if a user with the given email exists globally."""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.email == email.lower())
        )
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)
        result = await self.db.execute(stmt)
        return (result.scalar_one() or 0) > 0

    # ------------------------------------------------------------------
    # Paginated filtered query
    # ------------------------------------------------------------------

    async def get_paginated_users(
        self,
        user_type: Optional[int] = None,
        role_id: Optional[int] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Return (items, total_count, total_pages) with optional filtering.

        Supports ILIKE search on email, first_name, last_name.
        """
        conditions = []

        if not include_deleted:
            conditions.append(self.model.is_active == True)  # noqa: E712

        if user_type is not None:
            conditions.append(self.model.user_type == user_type)

        if role_id is not None:
            conditions.append(self.model.role_id == role_id)

        if search_query:
            pattern = f"%{search_query}%"
            conditions.append(
                or_(
                    self.model.email.ilike(pattern),
                    self.model.first_name.ilike(pattern),
                    self.model.last_name.ilike(pattern),
                )
            )

        # COUNT query
        count_stmt = select(func.count()).select_from(self.model)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        # Data query
        offset = (page - 1) * page_size
        data_stmt = select(self.model)
        if conditions:
            data_stmt = data_stmt.where(and_(*conditions))
        data_stmt = (
            data_stmt
            .order_by(self.model.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )

        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages
