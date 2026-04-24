"""
WorkspaceRequestRepository — async SQLAlchemy 2.x repository for the WorkspaceRequest model.
"""

from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseModel import row_to_dict
from src.base.BaseRepository import BaseRepository
from src.models.WorkspaceRequest import WorkspaceRequest


class WorkspaceRequestRepository(BaseRepository):
    """Repository for WorkspaceRequest entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(WorkspaceRequest, db)

    async def get_paginated_requests(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict], int, int]:
        """
        Return (items, total_count, total_pages) for active workspace requests.

        Optionally filters by status. Always restricts to is_active=True.
        Uses COUNT + LIMIT/OFFSET pattern matching BaseRepository.get_paginated.
        """
        conditions = [WorkspaceRequest.is_active == True]  # noqa: E712

        if status is not None:
            conditions.append(WorkspaceRequest.status == status)

        # --- COUNT query ---
        count_stmt = (
            select(func.count())
            .select_from(WorkspaceRequest)
            .where(and_(*conditions))
        )
        total_count: int = (await self.db.execute(count_stmt)).scalar_one()

        total_pages = max(1, (total_count + page_size - 1) // page_size)
        offset = (page - 1) * page_size

        # --- Data query ---
        data_stmt = (
            select(WorkspaceRequest)
            .where(and_(*conditions))
            .order_by(WorkspaceRequest.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        rows = (await self.db.execute(data_stmt)).scalars().all()

        return [row_to_dict(r) for r in rows], total_count, total_pages

    async def get_by_workspace_and_status(
        self,
        workspace_id: int,
        status: str,
    ) -> Optional[Dict]:
        """
        Return the first active WorkspaceRequest matching workspace_id and status.

        Returns None if no matching record exists.
        """
        stmt = (
            select(WorkspaceRequest)
            .where(
                and_(
                    WorkspaceRequest.workspace_id == workspace_id,
                    WorkspaceRequest.status == status,
                    WorkspaceRequest.is_active == True,  # noqa: E712
                )
            )
            .limit(1)
        )
        row = (await self.db.execute(stmt)).scalars().first()
        return row_to_dict(row) if row is not None else None

    async def has_pending_request(self, workspace_id: int) -> bool:
        """
        Return True if any active WorkspaceRequest with status='pending'
        exists for the given workspace_id.
        """
        stmt = (
            select(literal(1))
            .select_from(WorkspaceRequest)
            .where(
                and_(
                    WorkspaceRequest.workspace_id == workspace_id,
                    WorkspaceRequest.status == "pending",
                    WorkspaceRequest.is_active == True,  # noqa: E712
                )
            )
            .limit(1)
        )
        result = (await self.db.execute(stmt)).scalar()
        return result is not None

    async def get_referral_stats(self, days: int = 30) -> Dict:
        """
        Return referral statistics derived from workspace_requests.

        Computes:
        - Summary counts: total, by status, last N days vs previous N days
        - Per-referrer breakdown: name, email, counts by status, workspaces list
        """
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import case, distinct

        from src.models.User import User
        from src.models.Workspace import Workspace

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=days)
        prev_period_start = now - timedelta(days=days * 2)

        # ------------------------------------------------------------------
        # 1. Summary counts — total referrals and breakdown by status
        # ------------------------------------------------------------------
        summary_stmt = select(
            func.count().label("total"),
            func.count(case((WorkspaceRequest.status == "pending", 1))).label("pending"),
            func.count(case((WorkspaceRequest.status == "approved", 1))).label("approved"),
            func.count(case((WorkspaceRequest.status == "rejected", 1))).label("rejected"),
            func.count(case((WorkspaceRequest.created_at >= period_start, 1))).label("last_n_days"),
            func.count(case((
                and_(
                    WorkspaceRequest.created_at >= prev_period_start,
                    WorkspaceRequest.created_at < period_start,
                ), 1,
            ))).label("prev_n_days"),
            func.count(distinct(WorkspaceRequest.user_id)).label("total_referrers"),
        ).where(WorkspaceRequest.is_active == True)  # noqa: E712

        summary_row = (await self.db.execute(summary_stmt)).one()

        # ------------------------------------------------------------------
        # 2. Per-referrer aggregates — grouped by user_id
        # ------------------------------------------------------------------
        referrer_agg_stmt = (
            select(
                WorkspaceRequest.user_id,
                WorkspaceRequest.email,
                func.count().label("total"),
                func.count(case((WorkspaceRequest.status == "pending", 1))).label("pending"),
                func.count(case((WorkspaceRequest.status == "approved", 1))).label("approved"),
                func.count(case((WorkspaceRequest.status == "rejected", 1))).label("rejected"),
            )
            .where(WorkspaceRequest.is_active == True)  # noqa: E712
            .group_by(WorkspaceRequest.user_id, WorkspaceRequest.email)
            .order_by(func.count().desc())
        )
        referrer_rows = (await self.db.execute(referrer_agg_stmt)).all()

        # ------------------------------------------------------------------
        # 3. All referral records joined with workspace name for detail list
        # ------------------------------------------------------------------
        detail_stmt = (
            select(
                WorkspaceRequest.id,
                WorkspaceRequest.user_id,
                WorkspaceRequest.email,
                WorkspaceRequest.workspace_id,
                WorkspaceRequest.status,
                WorkspaceRequest.reviewed_at,
                WorkspaceRequest.rejection_reason,
                WorkspaceRequest.created_at,
                Workspace.name.label("workspace_name"),
                Workspace.is_active.label("workspace_active"),
                Workspace.is_verified.label("workspace_verified"),
                (User.first_name + " " + User.last_name).label("referrer_name"),
            )
            .outerjoin(Workspace, Workspace.id == WorkspaceRequest.workspace_id)
            .outerjoin(User, User.id == WorkspaceRequest.user_id)
            .where(WorkspaceRequest.is_active == True)  # noqa: E712
            .order_by(WorkspaceRequest.created_at.desc())
        )
        detail_rows = (await self.db.execute(detail_stmt)).all()

        # ------------------------------------------------------------------
        # 4. Fetch referrer full names for the aggregated list
        # ------------------------------------------------------------------
        user_ids = [r.user_id for r in referrer_rows if r.user_id is not None]
        user_map: Dict[int, Dict] = {}
        if user_ids:
            user_stmt = select(
                User.id,
                User.first_name,
                User.last_name,
                User.email,
            ).where(User.id.in_(user_ids))
            for u in (await self.db.execute(user_stmt)).all():
                user_map[u.id] = {
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "email": u.email,
                }

        # ------------------------------------------------------------------
        # 5. Build workspace detail list per referrer
        # ------------------------------------------------------------------
        workspaces_by_referrer: Dict[Optional[int], list] = {}
        for row in detail_rows:
            key = row.user_id
            if key not in workspaces_by_referrer:
                workspaces_by_referrer[key] = []
            workspaces_by_referrer[key].append({
                "request_id": row.id,
                "workspace_id": row.workspace_id,
                "workspace_name": row.workspace_name,
                "workspace_active": row.workspace_active,
                "workspace_verified": row.workspace_verified,
                "status": row.status,
                "rejection_reason": row.rejection_reason,
                "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
                "referred_at": row.created_at.isoformat() if row.created_at else None,
            })

        # ------------------------------------------------------------------
        # 6. Assemble top_referrers list
        # ------------------------------------------------------------------
        top_referrers = []
        for row in referrer_rows:
            uid = row.user_id
            user_info = user_map.get(uid, {})
            first = user_info.get("first_name", "")
            last = user_info.get("last_name", "")
            top_referrers.append({
                "user_id": uid,
                "name": f"{first} {last}".strip() or row.email,
                "email": user_info.get("email", row.email),
                "total": row.total,
                "pending": row.pending,
                "approved": row.approved,
                "rejected": row.rejected,
                "workspaces": workspaces_by_referrer.get(uid, []),
            })

        return {
            "summary_row": summary_row,
            "top_referrers": top_referrers,
        }
