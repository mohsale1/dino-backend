"""
ReviewRepository — async SQLAlchemy 2.x repository for the Review model.
One review per authenticated user per workspace enforced via partial unique index.
"""

import asyncio
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Review import Review
from src.models.User import User


# Columns selected for list/detail responses
_REVIEW_COLS = (
    Review.id,
    Review.workspace_id,
    Review.user_id,
    Review.rating,
    Review.comment,
    Review.is_approved,
    Review.is_active,
    Review.created_at,
    Review.updated_at,
)


class ReviewRepository(BaseRepository):
    """Repository for Review entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Review, db)

    # ------------------------------------------------------------------
    # Existence checks
    # ------------------------------------------------------------------

    async def user_has_review_for_workspace(
        self,
        user_id: int,
        workspace_id: int,
        exclude_id: Optional[int] = None,
    ) -> bool:
        """
        Return True if an active review from this user already exists
        for this workspace. Used to enforce one-review-per-user-per-workspace.
        """
        conditions = [
            Review.user_id == user_id,
            Review.workspace_id == workspace_id,
            Review.is_active.is_(True),
        ]
        if exclude_id is not None:
            conditions.append(Review.id != exclude_id)

        stmt = select(func.count()).select_from(Review).where(and_(*conditions))
        return (await self.db.execute(stmt)).scalar_one() > 0

    # ------------------------------------------------------------------
    # Read — paginated
    # ------------------------------------------------------------------

    async def get_paginated_reviews(
        self,
        workspace_id: int,
        is_approved: Optional[bool] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Return (items, total_count, total_pages).
        COUNT and DATA queries run in parallel.
        user_name built inline from LEFT JOIN.
        """
        conditions = [
            Review.workspace_id == workspace_id,
            Review.is_active.is_(is_active if is_active is not None else True),
        ]
        if is_approved is not None:
            conditions.append(Review.is_approved == is_approved)

        where_expr = and_(*conditions)
        offset = (page - 1) * page_size

        count_stmt = select(func.count()).select_from(Review).where(where_expr)
        data_stmt = (
            select(
                *_REVIEW_COLS,
                func.concat(
                    func.coalesce(User.first_name, ""),
                    " ",
                    func.coalesce(User.last_name, ""),
                ).label("user_name"),
            )
            .outerjoin(User, Review.user_id == User.id)
            .where(where_expr)
            .order_by(Review.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )

        total_result, rows = await asyncio.gather(
            self.db.execute(count_stmt),
            self.db.execute(data_stmt),
        )

        total: int = total_result.scalar_one() or 0
        total_pages = max(1, math.ceil(total / page_size))

        result = []
        for idx, row in enumerate(rows.all(), start=offset + 1):
            d = self._row_to_review_dict(row)
            d["index"] = idx
            result.append(d)

        return result, total, total_pages

    # ------------------------------------------------------------------
    # Read — approved (public)
    # ------------------------------------------------------------------

    async def get_approved_reviews(
        self,
        workspace_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return approved + active reviews for a workspace, newest first."""
        stmt = (
            select(
                *_REVIEW_COLS,
                func.concat(
                    func.coalesce(User.first_name, ""),
                    " ",
                    func.coalesce(User.last_name, ""),
                ).label("user_name"),
            )
            .outerjoin(User, Review.user_id == User.id)
            .where(
                Review.workspace_id == workspace_id,
                Review.is_approved.is_(True),
                Review.is_active.is_(True),
            )
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()
        return [self._row_to_review_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Read — single
    # ------------------------------------------------------------------

    async def get_by_id_for_workspace(
        self,
        review_id: int,
        workspace_id: int,
        include_deleted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Return a single review by id + workspace_id, with user_name."""
        conditions = [
            Review.id == review_id,
            Review.workspace_id == workspace_id,
        ]
        if not include_deleted:
            conditions.append(Review.is_active.is_(True))

        stmt = (
            select(
                *_REVIEW_COLS,
                func.concat(
                    func.coalesce(User.first_name, ""),
                    " ",
                    func.coalesce(User.last_name, ""),
                ).label("user_name"),
            )
            .outerjoin(User, Review.user_id == User.id)
            .where(and_(*conditions))
        )
        row = (await self.db.execute(stmt)).one_or_none()
        return self._row_to_review_dict(row) if row is not None else None

    # ------------------------------------------------------------------
    # Read — rating summary
    # ------------------------------------------------------------------

    async def get_rating_summary(self, workspace_id: int) -> Dict[str, Any]:
        """Return average_rating and total_reviews — single aggregation query."""
        stmt = select(
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("total"),
        ).where(
            Review.workspace_id == workspace_id,
            Review.is_approved.is_(True),
            Review.is_active.is_(True),
        )
        row = (await self.db.execute(stmt)).one_or_none()
        if row is None or not row.total:
            return {"average_rating": 0.0, "total_reviews": 0}
        return {
            "average_rating": round(float(row.avg_rating), 1) if row.avg_rating else 0.0,
            "total_reviews": row.total,
        }

    # ------------------------------------------------------------------
    # Write — scoped (single-query)
    # ------------------------------------------------------------------

    async def update_for_workspace(
        self,
        review_id: int,
        workspace_id: int,
        data: Dict[str, Any],
        include_deleted: bool = False,
    ) -> bool:
        """UPDATE a review scoped to workspace. Single round-trip."""
        conditions = [
            Review.id == review_id,
            Review.workspace_id == workspace_id,
        ]
        if not include_deleted:
            conditions.append(Review.is_active.is_(True))

        stmt = (
            update(Review)
            .where(and_(*conditions))
            .values(**data, updated_at=datetime.now(timezone.utc))
            .execution_options(synchronize_session=False)
        )
        return (await self.db.execute(stmt)).rowcount > 0

    async def soft_delete_for_workspace(self, review_id: int, workspace_id: int) -> bool:
        return await self.update_for_workspace(review_id, workspace_id, {"is_active": False})

    async def restore_for_workspace(self, review_id: int, workspace_id: int) -> bool:
        stmt = (
            update(Review)
            .where(
                Review.id == review_id,
                Review.workspace_id == workspace_id,
                Review.is_active.is_(False),
            )
            .values(is_active=True, updated_at=datetime.now(timezone.utc))
            .execution_options(synchronize_session=False)
        )
        return (await self.db.execute(stmt)).rowcount > 0

    async def approve_for_workspace(self, review_id: int, workspace_id: int) -> bool:
        return await self.update_for_workspace(review_id, workspace_id, {"is_approved": True})

    async def unapprove_for_workspace(self, review_id: int, workspace_id: int) -> bool:
        return await self.update_for_workspace(review_id, workspace_id, {"is_approved": False})

    # ------------------------------------------------------------------
    # Global / unscoped
    # ------------------------------------------------------------------

    async def get_global_average_rating(self) -> float:
        """Platform-wide average rating across all approved + active reviews."""
        stmt = select(func.avg(Review.rating)).where(
            Review.is_approved.is_(True),
            Review.is_active.is_(True),
        )
        avg = (await self.db.execute(stmt)).scalar_one_or_none()
        return round(float(avg), 1) if avg is not None else 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_review_dict(row: Any) -> Dict[str, Any]:
        """Convert a named-column row to a dict. Strips blank user_name to None."""
        d = row._asdict()
        user_name = d.get("user_name", "").strip()
        d["user_name"] = user_name if user_name else None
        # Coerce Decimal rating to float
        if "rating" in d and d["rating"] is not None:
            d["rating"] = float(d["rating"])
        # Coerce datetimes to ISO strings
        for field in ("created_at", "updated_at"):
            if field in d and d[field] is not None:
                val = d[field]
                if hasattr(val, "isoformat"):
                    d[field] = val.isoformat()
        return d
