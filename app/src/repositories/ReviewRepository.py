"""
ReviewRepository — async SQLAlchemy 2.x repository for the Review model.
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Review import Review
from src.models.User import User


class ReviewRepository(BaseRepository):
    """Repository for Review entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Review, db)

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    async def get_approved_reviews(
        self,
        workspace_id: int,
        persona_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Return approved + active reviews for a workspace scoped to a persona,
        newest first.

        Performs a LEFT OUTER JOIN against users so that first_name and
        last_name are available for user_name enrichment in the service layer.
        The user columns are surfaced as extra keys on each dict.
        """
        conditions = [
            Review.workspace_id == workspace_id,
            Review.persona_id == persona_id,
            Review.is_approved.is_(True),
            Review.is_active.is_(True),
        ]

        stmt = (
            select(
                Review,
                User.first_name.label("_user_first_name"),
                User.last_name.label("_user_last_name"),
            )
            .outerjoin(User, Review.user_id == User.id)
            .where(and_(*conditions))
            .order_by(Review.created_at.desc())
            .limit(limit)
        )

        rows = (await self.db.execute(stmt)).all()
        return self._map_rows_with_user(rows)

    async def get_paginated_reviews(
        self,
        workspace_id: int,
        persona_id: int,
        is_approved: Optional[bool] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Return a paginated list of reviews scoped to a persona with optional
        filters.

        Returns
        -------
        (items, total_count, total_pages)
        """
        # Always show only active reviews unless caller explicitly requests inactive
        conditions = [
            Review.workspace_id == workspace_id,
            Review.persona_id == persona_id,
            Review.is_active.is_(is_active if is_active is not None else True),
        ]

        if is_approved is not None:
            conditions.append(Review.is_approved == is_approved)

        where_expr = and_(*conditions)

        # COUNT query
        count_stmt = (
            select(func.count())
            .select_from(Review)
            .where(where_expr)
        )
        total: int = (await self.db.execute(count_stmt)).scalar_one()
        total_pages = max(1, math.ceil(total / page_size))

        # DATA query — LEFT JOIN users for name enrichment
        offset = (page - 1) * page_size
        data_stmt = (
            select(
                Review,
                User.first_name.label("_user_first_name"),
                User.last_name.label("_user_last_name"),
            )
            .outerjoin(User, Review.user_id == User.id)
            .where(where_expr)
            .order_by(Review.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )

        rows = (await self.db.execute(data_stmt)).all()
        return self._map_rows_with_user(rows), total, total_pages

    async def get_rating_summary(
        self,
        workspace_id: int,
        persona_id: int,
    ) -> Dict[str, Any]:
        """
        Return rating statistics for approved + active reviews scoped to a
        persona.

        Returns
        -------
        {
            "average_rating": float,
            "total_reviews": int,
            "rating_distribution": {1: N, 2: N, 3: N, 4: N, 5: N},
        }
        """
        conditions = [
            Review.workspace_id == workspace_id,
            Review.persona_id == persona_id,
            Review.is_approved.is_(True),
            Review.is_active.is_(True),
        ]

        where_expr = and_(*conditions)

        # Aggregate: average + count
        agg_stmt = select(
            func.avg(Review.rating).label("avg_rating"),
            func.count(Review.id).label("total"),
        ).where(where_expr)
        agg_row = (await self.db.execute(agg_stmt)).one_or_none()

        if agg_row is None:
            return {
                "average_rating": 0.0,
                "total_reviews": 0,
                "rating_distribution": {star: 0 for star in range(1, 6)},
            }

        total_reviews: int = agg_row.total or 0
        average_rating: float = round(float(agg_row.avg_rating), 2) if agg_row.avg_rating else 0.0

        # Distribution: one row per star value
        dist_stmt = (
            select(Review.rating, func.count(Review.id).label("cnt"))
            .where(where_expr)
            .group_by(Review.rating)
        )
        dist_rows = (await self.db.execute(dist_stmt)).all()
        distribution: Dict[int, int] = {star: 0 for star in range(1, 6)}
        for row in dist_rows:
            distribution[row.rating] = row.cnt

        return {
            "average_rating": average_rating,
            "total_reviews": total_reviews,
            "rating_distribution": distribution,
        }

    async def get_by_id_for_persona(
        self,
        review_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Return a single active review matched by id, workspace_id, and
        persona_id. Returns None when no matching row is found.

        Intended for ownership checks before scoped write operations.
        """
        stmt = select(Review).where(
            and_(
                Review.id == review_id,
                Review.workspace_id == workspace_id,
                Review.persona_id == persona_id,
                Review.is_active.is_(True),
            )
        )
        row = (await self.db.execute(stmt)).scalar_one_or_none()
        return row_to_dict(row) if row is not None else None

    async def update_for_persona(
        self,
        review_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """
        UPDATE a review WHERE id + workspace_id + persona_id + is_active=True.

        Automatically stamps updated_at. Returns True when exactly one row was
        affected, False otherwise.
        """
        payload = {
            **data,
            "updated_at": datetime.now(timezone.utc),
        }
        stmt = (
            update(Review)
            .where(
                and_(
                    Review.id == review_id,
                    Review.workspace_id == workspace_id,
                    Review.persona_id == persona_id,
                    Review.is_active.is_(True),
                )
            )
            .values(**payload)
        )
        result = await self.db.execute(stmt)
        return result.rowcount == 1

    async def soft_delete_for_persona(
        self,
        review_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """
        Soft-delete a review scoped to persona by setting is_active=False.
        """
        return await self.update_for_persona(
            review_id, workspace_id, persona_id, {"is_active": False}
        )

    async def restore_for_persona(
        self,
        review_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """
        Restore a soft-deleted review scoped to persona (is_active=False ->
        True). Targets only inactive rows so it cannot accidentally touch live
        records.
        """
        payload = {
            "is_active": True,
            "updated_at": datetime.now(timezone.utc),
        }
        stmt = (
            update(Review)
            .where(
                and_(
                    Review.id == review_id,
                    Review.workspace_id == workspace_id,
                    Review.persona_id == persona_id,
                    Review.is_active.is_(False),
                )
            )
            .values(**payload)
        )
        result = await self.db.execute(stmt)
        return result.rowcount == 1

    async def approve_for_persona(
        self,
        review_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Set is_approved=True scoped to persona."""
        return await self.update_for_persona(
            review_id, workspace_id, persona_id, {"is_approved": True}
        )

    async def unapprove_for_persona(
        self,
        review_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Set is_approved=False scoped to persona."""
        return await self.update_for_persona(
            review_id, workspace_id, persona_id, {"is_approved": False}
        )

    # ------------------------------------------------------------------
    # Global / unscoped write methods (no persona isolation)
    # ------------------------------------------------------------------

    async def get_global_average_rating(self) -> float:
        """
        Return the average rating across ALL approved + active reviews
        platform-wide (no workspace filter). Used for homepage stats.
        """
        stmt = select(func.avg(Review.rating)).where(
            Review.is_approved.is_(True),
            Review.is_active.is_(True),
        )
        avg = (await self.db.execute(stmt)).scalar_one_or_none()
        return round(float(avg), 2) if avg is not None else 0.0

    async def approve_review(self, review_id: int) -> bool:
        """Set is_approved=True for the given review (no persona scope)."""
        return await self.update(review_id, {"is_approved": True})

    async def unapprove_review(self, review_id: int) -> bool:
        """Set is_approved=False for the given review (no persona scope)."""
        return await self.update(review_id, {"is_approved": False})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_rows_with_user(rows: list) -> List[Dict[str, Any]]:
        """
        Convert joined (Review, first_name, last_name) rows to dicts.

        The private _user_first_name / _user_last_name keys are kept on the
        dict so the service layer can build user_name without an extra query.
        """
        result = []
        for row in rows:
            review_obj = row[0]
            first_name = row[1]
            last_name = row[2]
            d = row_to_dict(review_obj)
            d["_user_first_name"] = first_name
            d["_user_last_name"] = last_name
            result.append(d)
        return result