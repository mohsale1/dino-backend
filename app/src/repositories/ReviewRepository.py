from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Review import Review


class ReviewRepository(BaseRepository):
    """Review repository — async SQLAlchemy 2.x."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Review, db)

    # ------------------------------------------------------------------
    # Specialised read methods
    # ------------------------------------------------------------------

    async def get_approved_reviews(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return approved, active reviews ordered by newest first.

        Parameters
        ----------
        limit:
            When provided, caps the result set to this many rows.
        """
        stmt = (
            select(Review)
            .where(
                and_(
                    Review.is_active == True,  # noqa: E712
                    Review.is_approved == True,  # noqa: E712
                )
            )
            .order_by(Review.created_at.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        return [row_to_dict(row) for row in result.scalars().all()]

    async def get_by_workspace(
        self,
        workspace_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return active reviews for a workspace, newest first.

        Parameters
        ----------
        workspace_id:
            Scope filter.
        limit:
            When provided, caps the result set to this many rows.
        """
        stmt = (
            select(Review)
            .where(
                and_(
                    Review.is_active == True,  # noqa: E712
                    Review.workspace_id == workspace_id,
                )
            )
            .order_by(Review.created_at.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        return [row_to_dict(row) for row in result.scalars().all()]

    async def get_by_persona(
        self,
        persona_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return active reviews for a persona, newest first.

        Parameters
        ----------
        persona_id:
            Scope filter.
        limit:
            When provided, caps the result set to this many rows.
        """
        stmt = (
            select(Review)
            .where(
                and_(
                    Review.is_active == True,  # noqa: E712
                    Review.persona_id == persona_id,
                )
            )
            .order_by(Review.created_at.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        return [row_to_dict(row) for row in result.scalars().all()]
