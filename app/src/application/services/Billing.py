"""
BillingService — business logic for workspace billing.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.models.BillingDetail import BillingDetail
from src.models.BillingTransaction import BillingTransaction
from src.models.WorkspaceBilling import WorkspaceBilling


class BillingService:
    """Service for managing workspace billing information."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # BillingDetail
    # ------------------------------------------------------------------

    async def get_billing_detail(
        self, workspace_id: int
    ) -> Optional[Dict[str, Any]]:
        """Fetch billing_details for a workspace."""
        stmt = (
            select(BillingDetail)
            .where(BillingDetail.workspace_id == workspace_id)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row else None

    async def create_or_update_billing_detail(
        self, workspace_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upsert billing_details for a workspace using INSERT ... ON CONFLICT DO UPDATE."""
        now = datetime.now(timezone.utc)
        insert_values = {**data, "workspace_id": workspace_id, "updated_at": now}

        update_values = {k: v for k, v in data.items() if k != "workspace_id"}
        update_values["updated_at"] = now

        stmt = (
            pg_insert(BillingDetail)
            .values(**insert_values)
            .on_conflict_do_update(
                index_elements=["workspace_id"],
                set_=update_values,
            )
            .returning(BillingDetail)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        if row is None:
            raise RuntimeError("Billing detail upsert returned no row")
        return row_to_dict(row)


    # ------------------------------------------------------------------
    # WorkspaceBilling
    # ------------------------------------------------------------------

    async def get_workspace_billing(
        self, workspace_id: int
    ) -> Optional[Dict[str, Any]]:
        """Fetch workspace_billing for a workspace."""
        stmt = (
            select(WorkspaceBilling)
            .where(WorkspaceBilling.workspace_id == workspace_id)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        return row_to_dict(row) if row else None

    async def update_workspace_billing(
        self, workspace_id: int, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update workspace_billing fields."""
        stmt = (
            select(WorkspaceBilling)
            .where(WorkspaceBilling.workspace_id == workspace_id)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        row = result.scalars().first()
        if not row:
            return None
        for key, value in data.items():
            if hasattr(row, key):
                setattr(row, key, value)
        await self.db.flush()
        await self.db.refresh(row)
        return row_to_dict(row)

    # ------------------------------------------------------------------
    # BillingTransaction
    # ------------------------------------------------------------------

    async def get_billing_transactions(
        self,
        workspace_id: int,
        payment_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated billing transactions for a workspace."""
        conditions = [BillingTransaction.workspace_id == workspace_id]
        if payment_status is not None:
            conditions.append(BillingTransaction.payment_status == payment_status)

        where_expr = and_(*conditions)
        count_stmt = (
            select(func.count()).select_from(BillingTransaction).where(where_expr)
        )
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(BillingTransaction)
            .where(where_expr)
            .order_by(BillingTransaction.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages
