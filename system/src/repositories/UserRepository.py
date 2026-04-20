"""
UserRepository — async SQLAlchemy 2.x repository for the SystemUser model.

Deletion strategy: SystemUser has no is_deleted column.
A "deleted" user simply has is_active = False.
All queries filter by is_active unless explicitly told not to.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.SystemUser import SystemUser


class UserRepository(BaseRepository):
    """Repository for SystemUser entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(SystemUser, db)

    # ------------------------------------------------------------------
    # Simple lookups
    # ------------------------------------------------------------------

    async def get_by_role(self, role_id: str) -> List[Dict[str, Any]]:
        """Return all active system users assigned to the given role."""
        return await self.get_all(filters={"role_id": role_id})

    # ------------------------------------------------------------------
    # Existence check
    # ------------------------------------------------------------------

    async def email_exists(
        self, email: str, exclude_id: Optional[str] = None
    ) -> bool:
        """Return True if a system user with the given email exists."""
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
        role_id: Optional[str] = None,
        search_query: Optional[str] = None,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 10,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Return (items, total_count, total_pages) with optional filtering.

        active_only=True  → only is_active = True users (default)
        active_only=False → all users including deactivated/soft-deleted
        """
        conditions = []

        if active_only:
            conditions.append(self.model.is_active == True)  # noqa: E712

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
            count_stmt = count_stmt.where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        # Data query
        col = getattr(self.model, order_by, self.model.created_at)
        order_col = col.desc() if order_direction.lower() == "desc" else col.asc()
        offset = (page - 1) * page_size

        data_stmt = select(self.model)
        if conditions:
            data_stmt = data_stmt.where(*conditions)
        data_stmt = data_stmt.order_by(order_col).limit(page_size).offset(offset)

        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages
