"""
BillingService — workspace billing and billing transaction management.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.models.BillingTransaction import BillingTransaction
from src.models.Workspace import Workspace
from src.models.WorkspaceBilling import WorkspaceBilling
from src.repositories.WorkspaceRepository import WorkspaceRepository


class BillingService:
    """Billing service — async, SQLAlchemy-backed."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._ws_repo = WorkspaceRepository(db)

    # ------------------------------------------------------------------
    # Workspace billing
    # ------------------------------------------------------------------

    async def get_workspace_billing(self, workspace_id: int) -> Optional[Dict[str, Any]]:
        """Fetch workspace_billing record for a workspace."""
        stmt = select(WorkspaceBilling).where(WorkspaceBilling.workspace_id == workspace_id)
        result = await self._db.execute(stmt)
        obj = result.scalars().first()
        return row_to_dict(obj) if obj else None

    async def update_billing_info(
        self, workspace_id: int, data: Dict[str, Any]
    ) -> bool:
        """Update workspace_billing fields."""
        stmt = select(WorkspaceBilling).where(WorkspaceBilling.workspace_id == workspace_id)
        result = await self._db.execute(stmt)
        obj = result.scalars().first()
        if not obj:
            return False
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        obj.updated_at = datetime.now(timezone.utc)
        await self._db.flush()
        return True

    async def get_all_billing(
        self, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Paginated workspace_billing with workspace name."""
        count_stmt = select(func.count()).select_from(WorkspaceBilling)
        total = (await self._db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        stmt = (
            select(WorkspaceBilling, Workspace.name.label("workspace_name"))
            .join(Workspace, Workspace.id == WorkspaceBilling.workspace_id)
            .order_by(WorkspaceBilling.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        result = await self._db.execute(stmt)
        rows = result.all()

        items = []
        for billing_obj, workspace_name in rows:
            d = row_to_dict(billing_obj)
            d["workspace_name"] = workspace_name
            items.append(d)

        return items, total, total_pages

    async def get_billing_stats(self) -> Dict[str, Any]:
        """Aggregate counts by plan and plan_status."""
        from sqlalchemy import case

        stmt = select(
            func.count().label("total"),
            func.sum(
                case((WorkspaceBilling.plan_status == "active", 1), else_=0)
            ).label("active"),
            func.sum(
                case((WorkspaceBilling.plan_status == "inactive", 1), else_=0)
            ).label("inactive"),
            func.sum(
                case((WorkspaceBilling.plan == "free", 1), else_=0)
            ).label("free_plan"),
            func.sum(
                case((WorkspaceBilling.plan != "free", 1), else_=0)
            ).label("paid_plan"),
        )
        row = (await self._db.execute(stmt)).one()

        return {
            "total_workspaces": row.total,
            "active": int(row.active or 0),
            "inactive": int(row.inactive or 0),
            "free_plan": int(row.free_plan or 0),
            "paid_plan": int(row.paid_plan or 0),
        }



    # ------------------------------------------------------------------
    # Billing transactions
    # ------------------------------------------------------------------

    async def get_billing_transactions(
        self,
        workspace_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Paginated billing_transactions."""
        conditions = []
        if workspace_id is not None:
            conditions.append(BillingTransaction.workspace_id == workspace_id)

        count_stmt = select(func.count()).select_from(BillingTransaction)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = (await self._db.execute(count_stmt)).scalar_one() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        offset = (page - 1) * page_size
        data_stmt = select(BillingTransaction)
        if conditions:
            data_stmt = data_stmt.where(and_(*conditions))
        data_stmt = data_stmt.order_by(BillingTransaction.created_at.desc()).limit(page_size).offset(offset)

        rows = (await self._db.execute(data_stmt)).scalars().all()
        return [row_to_dict(r) for r in rows], total, total_pages


    async def create_billing_transaction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a billing_transaction record."""
        obj = BillingTransaction(**data)
        self._db.add(obj)
        await self._db.flush()
        await self._db.refresh(obj)
        return row_to_dict(obj)


    async def update_billing_transaction(
        self, transaction_id: int, data: Dict[str, Any]
    ) -> bool:
        """Update payment_status, paid_amount, last_paid_at, payment_ref."""
        from sqlalchemy import update

        allowed_fields = {"payment_status", "paid_amount", "last_paid_at", "payment_ref", "notes"}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        update_data["updated_at"] = datetime.now(timezone.utc)

        stmt = (
            update(BillingTransaction)
            .where(BillingTransaction.id == transaction_id)
            .values(**update_data)
            .execution_options(synchronize_session=False)
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0

