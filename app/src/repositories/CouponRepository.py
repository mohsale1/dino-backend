from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.Coupon import Coupon


class CouponRepository(BaseRepository):
    """Coupon repository — async SQLAlchemy 2.x."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Coupon, db)

    # ------------------------------------------------------------------
    # Specialised read methods
    # ------------------------------------------------------------------

    async def get_by_code(
        self,
        code: str,
        workspace_id: str,
        include_deleted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Look up a coupon by its code within a specific workspace.

        Returns the first matching row as a dict, or None when not found.
        The composite unique constraint (code, workspace_id) guarantees at
        most one result, so LIMIT 1 is a safety net only.
        """
        clauses: list = [
            Coupon.code == code,
            Coupon.workspace_id == workspace_id,
        ]

        if not include_deleted:
            clauses.append(Coupon.is_active == True)  # noqa: E712

        stmt = select(Coupon).where(and_(*clauses)).limit(1)
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row is not None else None

    async def get_by_workspace(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 10,
        is_available: Optional[bool] = None,
        order_by: str = "created_at",
        order_direction: str = "desc",
        include_deleted: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Paginated coupons scoped to a workspace.

        Parameters
        ----------
        workspace_id:
            Required scope filter.
        is_available:
            Optional boolean filter on is_available.
        include_deleted:
            When False (default), excludes soft-deleted rows.

        Returns
        -------
        (items, total_count, total_pages)
        """
        filters: Dict[str, Any] = {"workspace_id": workspace_id}

        if is_available is not None:
            filters["is_available"] = is_available

        return await self.get_paginated(
            page=page,
            page_size=page_size,
            filters=filters,
            include_deleted=include_deleted,
            order_by=order_by,
            order_direction=order_direction,
        )

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    async def increment_usage(self, coupon_id: str) -> bool:
        """
        Atomically increment usage_count by 1 for the given coupon.

        Uses a SQL UPDATE expression (usage_count = usage_count + 1) so the
        operation is safe under concurrent requests without a read-modify-write
        cycle.

        Returns True when a row was matched and updated, False otherwise.
        """
        stmt = (
            update(Coupon)
            .where(Coupon.id == coupon_id)
            .values(usage_count=Coupon.usage_count + 1)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def validate_and_apply(
        self,
        code: str,
        workspace_id: str,
        order_amount: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically validate and consume one coupon use in a single UPDATE.

        Eliminates the TOCTOU race between a separate validate + apply pair by
        issuing a single conditional UPDATE … RETURNING statement:

            UPDATE coupons
            SET    usage_count = usage_count + 1
            WHERE  code          = :code
              AND  workspace_id  = :workspace_id
              AND  is_active     = TRUE
              AND  is_available  = TRUE
              AND  (usage_limit IS NULL OR usage_count < usage_limit)
              AND  (valid_from   IS NULL OR valid_from  <= :now)
              AND  (valid_until  IS NULL OR valid_until >= :now)
              AND  (min_order_amount IS NULL OR min_order_amount <= :order_amount)
            RETURNING *

        Returns the updated coupon row as a dict when the update succeeds
        (coupon is valid and a use was consumed), or None when no row matched
        (coupon not found, exhausted, inactive, outside its validity window,
        or below the minimum order amount).
        """
        now = datetime.now(timezone.utc)
        stmt = text(
            "UPDATE coupons "
            "SET usage_count = usage_count + 1 "
            "WHERE code         = :code "
            "  AND workspace_id = :workspace_id "
            "  AND is_active    = TRUE "
            "  AND is_available = TRUE "
            "  AND (usage_limit IS NULL OR usage_count < usage_limit) "
            "  AND (valid_from  IS NULL OR valid_from  <= :now) "
            "  AND (valid_until IS NULL OR valid_until >= :now) "
            "  AND (min_order_amount IS NULL OR min_order_amount <= :order_amount) "
            "RETURNING *"
        )
        result = await self.db.execute(
            stmt,
            {
                "code": code,
                "workspace_id": workspace_id,
                "now": now,
                "order_amount": order_amount,
            },
        )
        row = result.mappings().first()
        return dict(row) if row is not None else None


    async def apply_coupon_atomic(
        self, coupon_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        TOCTOU-safe atomic coupon application.

        Issues a single UPDATE ... RETURNING that increments usage_count only
        when all validity conditions are met in one database round-trip:

        - The coupon is active (is_active = true)
        - The coupon is available (is_available = true)
        - The usage limit has not been reached
          (usage_limit IS NULL OR usage_count < usage_limit)

        Returns a dict with ``id`` and ``usage_count`` of the updated row, or
        None when no row was matched (coupon exhausted, inactive, or not found).
        """
        stmt = (
            update(Coupon)
            .where(
                and_(
                    Coupon.id == coupon_id,
                    Coupon.is_active == True,   # noqa: E712
                    Coupon.is_available == True,  # noqa: E712
                    (Coupon.usage_limit.is_(None))
                    | (Coupon.usage_count < Coupon.usage_limit),
                )
            )
            .values(usage_count=Coupon.usage_count + 1)
            .execution_options(synchronize_session=False)
            .returning(Coupon.id, Coupon.usage_count)
        )
        result = await self.db.execute(stmt)
        row = result.first()
        return {"id": str(row.id), "usage_count": row.usage_count} if row else None

