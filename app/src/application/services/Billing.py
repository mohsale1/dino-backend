"""
BillingService — business logic for workspace billing.
Covers: WorkspaceBilling, BillingDetail, BillingTransaction, BillingConfig.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, cast, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.models.BillingConfig import BillingConfig
from src.models.BillingDetail import BillingDetail
from src.models.BillingTransaction import BillingTransaction
from src.models.Workspace import Workspace
from src.models.WorkspaceBilling import WorkspaceBilling

logger = logging.getLogger(__name__)


class BillingService:
    """Service for managing workspace billing information."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

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
        row = (await self.db.execute(stmt)).scalars().first()
        return row_to_dict(row) if row else None

    async def update_workspace_billing(
        self, workspace_id: int, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update workspace_billing fields — single round-trip UPDATE."""
        from datetime import datetime, timezone
        from sqlalchemy import update as sa_update

        payload = {**data, "updated_at": datetime.now(timezone.utc)}
        stmt = (
            sa_update(WorkspaceBilling)
            .where(WorkspaceBilling.workspace_id == workspace_id)
            .values(**payload)
            .execution_options(synchronize_session=False)
            .returning(WorkspaceBilling)
        )
        result = (await self.db.execute(stmt)).scalars().first()
        if result is None:
            return None
        logger.info(
            "billing.workspace.updated workspace_id=%s fields=%s",
            workspace_id, list(data.keys()),
        )
        return row_to_dict(result)

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
        row = (await self.db.execute(stmt)).scalars().first()
        return row_to_dict(row) if row else None

    async def create_or_update_billing_detail(
        self, workspace_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Upsert billing_details for a workspace — INSERT ... ON CONFLICT DO UPDATE."""
        now = datetime.now(timezone.utc)
        insert_values = {**data, "workspace_id": workspace_id, "updated_at": now}
        update_values = {k: v for k, v in data.items() if k != "workspace_id"}
        update_values["updated_at"] = now

        await self.db.execute(
            pg_insert(BillingDetail)
            .values(**insert_values)
            .on_conflict_do_update(
                index_elements=["workspace_id"],
                set_=update_values,
            )
        )

        row = (
            await self.db.execute(
                select(BillingDetail)
                .where(BillingDetail.workspace_id == workspace_id)
                .limit(1)
            )
        ).scalars().first()

        if row is None:
            raise RuntimeError("Billing detail upsert returned no row")

        logger.info("billing.detail.upserted workspace_id=%s", workspace_id)
        return row_to_dict(row)

    # ------------------------------------------------------------------
    # BillingConfig (per-persona tax/service charge config)
    # ------------------------------------------------------------------

    async def get_billing_config(
        self, workspace_id: int, persona_id: int
    ) -> Optional[Dict[str, Any]]:
        """Fetch billing config for a workspace+persona pair."""
        stmt = (
            select(BillingConfig)
            .where(
                BillingConfig.workspace_id == workspace_id,
                BillingConfig.persona_id == persona_id,
                BillingConfig.is_active.is_(True),
            )
            .limit(1)
        )
        row = (await self.db.execute(stmt)).scalars().first()
        return row_to_dict(row) if row else None

    async def upsert_billing_config(
        self, workspace_id: int, persona_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upsert billing config for a workspace+persona pair.
        Rates are stored as fractional values (0.05 = 5%).
        """
        now = datetime.now(timezone.utc)
        insert_values = {
            **data,
            "workspace_id": workspace_id,
            "persona_id": persona_id,
            "is_active": True,
            "updated_at": now,
        }
        update_values = {k: v for k, v in data.items()}
        update_values["updated_at"] = now

        await self.db.execute(
            pg_insert(BillingConfig)
            .values(**insert_values)
            .on_conflict_do_update(
                constraint="uq_billing_config_workspace_persona",
                set_=update_values,
            )
        )

        row = (
            await self.db.execute(
                select(BillingConfig)
                .where(
                    BillingConfig.workspace_id == workspace_id,
                    BillingConfig.persona_id == persona_id,
                )
                .limit(1)
            )
        ).scalars().first()

        if row is None:
            raise RuntimeError("Billing config upsert returned no row")

        logger.info(
            "billing.config.upserted workspace_id=%s persona_id=%s",
            workspace_id, persona_id,
        )
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

        count_stmt = select(func.count()).select_from(BillingTransaction).where(where_expr)
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

        result = []
        for idx, row in enumerate(rows, start=offset + 1):
            d = row_to_dict(row)
            d["index"] = idx
            result.append(d)

        return result, total, total_pages

    # ------------------------------------------------------------------
    # Billing overview — full summary for UI dashboard card
    # ------------------------------------------------------------------

    async def get_billing_overview(
        self, workspace_id: int
    ) -> Dict[str, Any]:
        """
        Return a complete billing overview for the UI:
          - plan info (WorkspaceBilling)
          - billing detail (BillingDetail)
          - transaction summary (total paid, pending, last payment)
        All queries run in parallel.
        """
        async def _get_billing():
            stmt = select(WorkspaceBilling).where(
                WorkspaceBilling.workspace_id == workspace_id
            ).limit(1)
            row = (await self.db.execute(stmt)).scalars().first()
            return row_to_dict(row) if row else None

        async def _get_detail():
            stmt = select(BillingDetail).where(
                BillingDetail.workspace_id == workspace_id
            ).limit(1)
            row = (await self.db.execute(stmt)).scalars().first()
            return row_to_dict(row) if row else None

        async def _get_transaction_summary():
            stmt = select(
                func.count(BillingTransaction.id).label("total_transactions"),
                func.coalesce(func.sum(BillingTransaction.paid_amount), 0).label("total_paid"),
                func.count(
                    BillingTransaction.id
                ).filter(BillingTransaction.payment_status == "pending").label("pending_count"),
                func.max(BillingTransaction.last_paid_at).label("last_paid_at"),
            ).where(BillingTransaction.workspace_id == workspace_id)
            row = (await self.db.execute(stmt)).one_or_none()
            if row is None:
                return {
                    "total_transactions": 0,
                    "total_paid": 0.0,
                    "pending_count": 0,
                    "last_paid_at": None,
                }
            return {
                "total_transactions": row.total_transactions,
                "total_paid": float(row.total_paid),
                "pending_count": row.pending_count,
                "last_paid_at": row.last_paid_at.isoformat() if row.last_paid_at else None,
            }

        billing, detail, tx_summary = await asyncio.gather(
            _get_billing(),
            _get_detail(),
            _get_transaction_summary(),
        )

        logger.debug("billing.overview workspace_id=%s", workspace_id)
        return {
            "workspace_id": workspace_id,
            "billing": billing,
            "billing_detail": detail,
            "transaction_summary": tx_summary,
        }

    # ------------------------------------------------------------------
    # Billing due workspaces — for admin/system use
    # ------------------------------------------------------------------

    async def get_billing_due_workspaces(
        self,
        page: int = 1,
        page_size: int = 20,
        overdue_only: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Return paginated workspaces whose billing is due or overdue.

        Due = next_billing_date <= today AND plan_status = 'active'
        Overdue = next_billing_date < today (past due)

        Joins WorkspaceBilling → Workspace to include workspace name.
        """
        today = datetime.now(timezone.utc).date()

        conditions = [
            WorkspaceBilling.plan_status == "active",
            WorkspaceBilling.next_billing_date.isnot(None),
            cast(WorkspaceBilling.next_billing_date, type_=None).isnot(None),
        ]

        if overdue_only:
            # Strictly past due
            conditions.append(
                func.date(WorkspaceBilling.next_billing_date) < today
            )
        else:
            # Due today or earlier
            conditions.append(
                func.date(WorkspaceBilling.next_billing_date) <= today
            )

        where_expr = and_(*conditions)

        count_stmt = (
            select(func.count())
            .select_from(WorkspaceBilling)
            .where(where_expr)
        )
        total = (await self.db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = (
            select(
                WorkspaceBilling.id,
                WorkspaceBilling.workspace_id,
                WorkspaceBilling.plan,
                WorkspaceBilling.plan_status,
                WorkspaceBilling.billing_cycle,
                WorkspaceBilling.billing_email,
                WorkspaceBilling.billing_name,
                WorkspaceBilling.next_billing_date,
                Workspace.name.label("workspace_name"),
                Workspace.is_active.label("workspace_active"),
            )
            .join(Workspace, Workspace.id == WorkspaceBilling.workspace_id)
            .where(where_expr)
            .order_by(WorkspaceBilling.next_billing_date.asc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).all()

        result = []
        for idx, row in enumerate(rows, start=offset + 1):
            d = dict(row._mapping)
            d["index"] = idx
            # Coerce datetime to ISO string
            if d.get("next_billing_date") and hasattr(d["next_billing_date"], "isoformat"):
                d["next_billing_date"] = d["next_billing_date"].isoformat()
            # Days overdue
            if d.get("next_billing_date"):
                try:
                    due_date = datetime.fromisoformat(d["next_billing_date"]).date()
                    d["days_overdue"] = max(0, (today - due_date).days)
                except Exception:
                    d["days_overdue"] = 0
            result.append(d)

        logger.info(
            "billing.due_workspaces total=%s overdue_only=%s page=%s",
            total, overdue_only, page,
        )
        return result, total, total_pages
