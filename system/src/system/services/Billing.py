from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.models.Workspace import Workspace
from src.repositories.WorkspaceRepository import WorkspaceRepository


class BillingService(BaseService):
    """Billing service — async, SQLAlchemy-backed."""

    PLAN_PRICING: Dict[str, float] = {
        'free':       0.0,
        'basic':      49.0,
        'standard':   99.0,
        'premium':    149.0,
        'pro':        199.0,
        'enterprise': 299.0,
    }

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        super().__init__(WorkspaceRepository(db))

    # ------------------------------------------------------------------
    # Pure-Python helpers (no DB access — kept sync)
    # ------------------------------------------------------------------

    def _get_plan_amount(self, plan: str) -> float:
        """Return the monthly price for *plan*."""
        if not plan:
            return 0.0
        plan_lower = plan.lower()
        for plan_name, price in self.PLAN_PRICING.items():
            if plan_name in plan_lower:
                return price
        return 0.0

    def _calculate_next_billing_date(self, workspace: Dict[str, Any]) -> Optional[str]:
        """Calculate the next billing date for *workspace* (pure Python, no DB).

        Uses a fixed 30-day billing interval.  If next_billing_date is already
        set and in the future it is returned as-is.
        """
        subscription_status = workspace.get('subscription_status', '').lower()
        if subscription_status not in ('active', 'trial'):
            return None

        now = datetime.now(timezone.utc)

        # Honour an already-set future next_billing_date
        existing = workspace.get('next_billing_date')
        if existing:
            try:
                if isinstance(existing, str):
                    next_dt = datetime.fromisoformat(existing.replace('Z', '+00:00'))
                else:
                    next_dt = existing
                if next_dt.tzinfo is None:
                    next_dt = next_dt.replace(tzinfo=timezone.utc)
                if next_dt > now:
                    return next_dt.isoformat()
            except (ValueError, TypeError, AttributeError):
                pass

        # Derive from subscription_start_date or created_at, rolling forward in
        # 30-day increments until the next date is in the future.
        start_date = workspace.get('subscription_start_date') or workspace.get('created_at')
        if start_date:
            try:
                if isinstance(start_date, str):
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                else:
                    start_dt = start_date
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                next_billing = start_dt + timedelta(days=30)
                while next_billing < now:
                    next_billing += timedelta(days=30)
                return next_billing.isoformat()
            except (ValueError, TypeError, AttributeError):
                pass

        return (now + timedelta(days=30)).isoformat()

    # ------------------------------------------------------------------
    # Async public methods
    # ------------------------------------------------------------------

    async def get_workspace_billing(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get full billing information for a single workspace."""
        workspace = await self.get_by_id(workspace_id)
        if not workspace:
            return None

        subscription_plan = workspace.get('subscription_plan', 'Free')
        next_billing_date = self._calculate_next_billing_date(workspace)
        amount = self._get_plan_amount(subscription_plan)

        return {
            'workspace_id':            workspace.get('id'),
            'workspace_name':          workspace.get('name'),
            # Subscription
            'subscription_plan':       subscription_plan,
            'subscription_status':     workspace.get('subscription_status', 'Active'),
            # Billing contact
            'billing_name':            workspace.get('billing_name'),
            'billing_email':           workspace.get('billing_email'),
            'billing_phone':           workspace.get('billing_phone'),
            'billing_address':         workspace.get('billing_address'),
            'billing_city':            workspace.get('billing_city'),
            'billing_state':           workspace.get('billing_state'),
            'billing_postal_code':     workspace.get('billing_postal_code'),
            'billing_country':         workspace.get('billing_country'),
            # Payment
            'amount':                  amount,
            'mrr':                     float(workspace.get('mrr') or 0),
            # Dates
            'subscription_start_date': workspace.get('subscription_start_date'),
            'next_billing_date':       next_billing_date,
        }

    async def update_subscription(self, workspace_id: str, plan: str, status: str) -> bool:
        """Update subscription plan and status, recalculating MRR."""
        workspace = await self.get_by_id(workspace_id)
        if not workspace:
            return False

        mrr = self._get_plan_amount(plan)

        update_data: Dict[str, Any] = {
            'subscription_plan':   plan,
            'subscription_status': status,
            'mrr':                 mrr,
        }

        if status.lower() == 'active' and not workspace.get('subscription_start_date'):
            update_data['subscription_start_date'] = datetime.now(timezone.utc)

        workspace_updated = {**workspace, **update_data}
        next_billing = self._calculate_next_billing_date(workspace_updated)
        if next_billing:
            update_data['next_billing_date'] = next_billing

        return await self.update(workspace_id, update_data)

    async def process_billing(self, workspace_id: str) -> Dict[str, Any]:
        """Process a billing event for a workspace (called on billing date)."""
        workspace = await self.get_by_id(workspace_id)
        if not workspace:
            return {'success': False, 'message': 'Workspace not found'}

        subscription_plan = workspace.get('subscription_plan', 'Free')
        amount = self._get_plan_amount(subscription_plan)

        now = datetime.now(timezone.utc)
        next_billing = now + timedelta(days=30)

        update_data: Dict[str, Any] = {
            'next_billing_date': next_billing,
        }

        await self.update(workspace_id, update_data)

        return {
            'success':           True,
            'message':           'Billing processed successfully',
            'amount':            amount,
            'next_billing_date': next_billing.isoformat(),
        }

    async def get_all_billing_info(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get summarised billing information for all workspaces (paginated)."""
        items, _total, _pages = await self.get_paginated(
            page=page,
            page_size=page_size,
            order_by='created_at',
            order_direction='desc',
        )
        return [
            {
                'workspace_id':        ws.get('id'),
                'workspace_name':      ws.get('name'),
                'billing_email':       ws.get('billing_email'),
                'subscription_plan':   ws.get('subscription_plan', 'Free'),
                'subscription_status': ws.get('subscription_status', 'Active'),
                'next_billing_date':   self._calculate_next_billing_date(ws),
                'amount':              self._get_plan_amount(ws.get('subscription_plan', 'Free')),
                'mrr':                 float(ws.get('mrr') or 0),
            }
            for ws in items
        ]

    async def get_paginated_billing_info(
        self,
        page: int = 1,
        page_size: int = 10,
        order_by: str = 'created_at',
        order_direction: str = 'desc',
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Get paginated billing information for all workspaces."""
        items, total, total_pages = await self.get_paginated(
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_direction=order_direction,
        )

        billing_info = [
            {
                'workspace_id':        ws.get('id'),
                'workspace_name':      ws.get('name'),
                'billing_email':       ws.get('billing_email'),
                'subscription_plan':   ws.get('subscription_plan', 'Free'),
                'subscription_status': ws.get('subscription_status', 'Active'),
                'next_billing_date':   self._calculate_next_billing_date(ws),
                'amount':              self._get_plan_amount(ws.get('subscription_plan', 'Free')),
                'mrr':                 float(ws.get('mrr') or 0),
                'created_at':          ws.get('created_at'),
            }
            for ws in items
        ]

        return billing_info, total, total_pages

    async def get_billing_stats(self) -> Dict[str, Any]:
        """Aggregate billing statistics across all workspaces via SQL."""
        stmt = select(
            # Status counts
            func.count().label('total'),
            func.count(
                case((func.lower(Workspace.subscription_status) == 'active', 1))
            ).label('active'),
            func.count(
                case((func.lower(Workspace.subscription_status) == 'trial', 1))
            ).label('trial'),
            func.count(
                case((func.lower(Workspace.subscription_status) == 'past due', 1))
            ).label('past_due'),
            func.count(
                case((func.lower(Workspace.subscription_status) == 'cancelled', 1))
            ).label('cancelled'),
            # MRR sum for active workspaces only
            func.coalesce(
                func.sum(
                    case((func.lower(Workspace.subscription_status) == 'active', Workspace.mrr))
                ),
                0,
            ).label('total_mrr'),
        ).where(Workspace.is_active == True)  # noqa: E712

        row = (await self._db.execute(stmt)).one()

        total_subscriptions  = row.total
        active_subscriptions = row.active
        trial_subscriptions  = row.trial
        past_due             = row.past_due
        cancelled            = row.cancelled
        monthly_revenue      = round(float(row.total_mrr), 2)

        return {
            'total_subscriptions':      total_subscriptions,
            'active_subscriptions':     active_subscriptions,
            'trial_subscriptions':      trial_subscriptions,
            'past_due':                 past_due,
            'cancelled':                cancelled,
            'monthly_revenue':          monthly_revenue,
            'yearly_revenue':           round(monthly_revenue * 12, 2),
            'average_revenue_per_user': round(monthly_revenue / max(1, active_subscriptions), 2),
        }

    async def get_upcoming_renewals(self, days: int = 7) -> List[Dict[str, Any]]:
        """Return active workspaces whose next billing date falls within *days*.

        Loads workspaces in pages to avoid fetching the entire table at once.
        """
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days)

        upcoming: List[Dict[str, Any]] = []
        page = 1
        page_size = 100

        while True:
            items, _total, total_pages = await self.get_paginated(
                page=page,
                page_size=page_size,
                order_by='next_billing_date',
                order_direction='asc',
            )

            for ws in items:
                if ws.get('subscription_status', '').lower() != 'active':
                    continue

                next_billing = self._calculate_next_billing_date(ws)
                if not next_billing:
                    continue

                try:
                    next_dt = datetime.fromisoformat(next_billing.replace('Z', '+00:00'))
                    if next_dt.tzinfo is None:
                        next_dt = next_dt.replace(tzinfo=timezone.utc)
                    if now <= next_dt <= cutoff:
                        upcoming.append({
                            'workspace_id':      ws.get('id'),
                            'workspace_name':    ws.get('name'),
                            'next_billing_date': next_billing,
                            'amount':            self._get_plan_amount(
                                ws.get('subscription_plan', 'Free')
                            ),
                            'mrr':               float(ws.get('mrr') or 0),
                            'billing_email':     ws.get('billing_email'),
                        })
                except (ValueError, TypeError, AttributeError):
                    pass

            if page >= total_pages:
                break
            page += 1

        return upcoming
