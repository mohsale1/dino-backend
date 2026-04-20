"""
System Dashboard Service
Provides analytics and statistics for system administrators.
All queries are executed directly against PostgreSQL via SQLAlchemy async —
no Firestore / Firebase dependencies.
"""

from typing import Any, Dict, List
from datetime import datetime, timezone, timedelta

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.Persona import Persona
from src.models.Role import Role
from src.models.SystemUser import SystemUser
from src.models.Workspace import Workspace


class SystemDashboardService:
    """Service for system-level dashboard data and analytics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public async methods
    # ------------------------------------------------------------------

    async def get_system_stats(self) -> Dict[str, Any]:
        """Return overall system statistics using a single SQL aggregation."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago  = now - timedelta(days=60)

        # --- Single query: all Workspace counts in one pass ---------------
        ws_row = (
            await self.db.execute(
                select(
                    func.count().label('total'),
                    func.count(
                        case((Workspace.updated_at >= thirty_days_ago, 1))
                    ).label('active'),
                    func.count(
                        case((Workspace.created_at >= thirty_days_ago, 1))
                    ).label('last_30'),
                    func.count(
                        case((
                            and_(
                                Workspace.created_at >= sixty_days_ago,
                                Workspace.created_at < thirty_days_ago,
                            ),
                            1,
                        ))
                    ).label('prev_30'),
                ).where(Workspace.is_active == True)  # noqa: E712
            )
        ).one()

        # --- Single query: all SystemUser counts in one pass --------------
        su_row = (
            await self.db.execute(
                select(
                    func.count().label('total'),
                    func.count(
                        case((SystemUser.last_login >= thirty_days_ago, 1))
                    ).label('active'),
                ).where(SystemUser.is_active == True)  # noqa: E712
            )
        ).one()

        # --- Persona count ------------------------------------------------
        total_personas: int = (
            await self.db.execute(
                select(func.count()).select_from(Persona).where(Persona.is_active == True)  # noqa: E712
            )
        ).scalar_one()

        # application_users lives in dino-application DB — cross-service boundary.
        total_app_users = 0
        users_last_30   = 0

        workspace_growth = _calculate_growth_percentage(ws_row.prev_30, ws_row.last_30)

        return {
            'total_workspaces':        ws_row.total,
            'active_workspaces':       ws_row.active,
            'total_system_users':      su_row.total,
            'active_system_users':     su_row.active,
            'total_app_users':         total_app_users,
            'total_personas':          total_personas,
            'workspace_growth':        workspace_growth,
            'user_growth':             '0%',
            'workspaces_last_30_days': ws_row.last_30,
            'users_last_30_days':      users_last_30,
        }

    async def get_workspace_growth_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Return cumulative workspace counts for each day over the last *days* days.

        Fetches only the created_at timestamps within the window (not full rows)
        and computes the cumulative count in Python — one lightweight query.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        stmt = (
            select(Workspace.created_at)
            .where(
                and_(
                    Workspace.is_active == True,  # noqa: E712
                    Workspace.created_at >= start_date,
                )
            )
            .order_by(Workspace.created_at)
        )
        result = await self.db.execute(stmt)
        all_dates = [row[0] for row in result.all()]

        growth_data: List[Dict[str, Any]] = []
        for i in range(days + 1):
            day = start_date + timedelta(days=i)
            # Keep date_end timezone-aware so it compares correctly with
            # timezone-aware created_at values from the database.
            date_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            count = sum(1 for d in all_dates if d and d <= date_end)
            growth_data.append({
                'date':   day.strftime('%Y-%m-%d'),
                'period': day.strftime('%b %d'),
                'count':  count,
            })

        return growth_data

    async def get_user_distribution(self) -> List[Dict[str, Any]]:
        """Return system-user counts grouped by role name (SQL GROUP BY)."""
        stmt = (
            select(Role.name, func.count(SystemUser.id).label('count'))
            .join(Role, SystemUser.role_id == Role.id)
            .where(SystemUser.is_active == True)  # noqa: E712
            .group_by(Role.name)
        )
        result = await self.db.execute(stmt)
        return [{'role': row.name, 'count': row.count} for row in result.all()]

    async def get_top_onboarders(self, limit: int = 5) -> List[Dict[str, Any]]:  # noqa: ARG002
        """
        Return the system users who onboarded the most application users.

        application_users lives in the dino-application database — a different
        AsyncSession / connection pool.  Cross-service queries are not supported
        here; callers should aggregate this via an inter-service API call.
        """
        return []

    async def get_recent_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent system activity from the last 24 hours."""
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        activities: List[Dict[str, Any]] = []

        # Recent system-user logins — select only the columns we need.
        login_stmt = (
            select(SystemUser.id, SystemUser.email, SystemUser.last_login)
            .where(
                and_(
                    SystemUser.is_active == True,  # noqa: E712
                    SystemUser.last_login >= twenty_four_hours_ago,
                )
            )
            .order_by(SystemUser.last_login.desc())
            .limit(10)
        )
        login_result = await self.db.execute(login_stmt)
        for row in login_result.all():
            activities.append({
                'id':        f'login_{row.id}',
                'type':      'login',
                'user':      row.email,
                'action':    'Logged in',
                'target':    '',
                'time':      _get_time_ago(row.last_login),
                'timestamp': row.last_login.isoformat() if row.last_login else '',
            })

        # Recently created workspaces — select only the columns we need.
        ws_stmt = (
            select(Workspace.id, Workspace.name, Workspace.created_at)
            .where(
                and_(
                    Workspace.is_active == True,  # noqa: E712
                    Workspace.created_at >= twenty_four_hours_ago,
                )
            )
            .order_by(Workspace.created_at.desc())
            .limit(10)
        )
        ws_result = await self.db.execute(ws_stmt)
        for row in ws_result.all():
            activities.append({
                'id':        f'workspace_{row.id}',
                'type':      'workspace_created',
                'user':      'System',
                'action':    'Created new workspace',
                'target':    row.name,
                'time':      _get_time_ago(row.created_at),
                'timestamp': row.created_at.isoformat() if row.created_at else '',
            })

        activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return activities[:limit]

    async def get_subscription_stats(self) -> Dict[str, Any]:
        """Return subscription and MRR statistics via a single SQL aggregation."""
        status_col = func.lower(Workspace.subscription_status)

        row = (
            await self.db.execute(
                select(
                    func.count(
                        case((status_col == 'active', 1))
                    ).label('active'),
                    func.count(
                        case((status_col == 'past due', 1))
                    ).label('past_due'),
                    func.count(
                        case((status_col == 'trial', 1))
                    ).label('trial'),
                    func.coalesce(
                        func.sum(
                            case((status_col == 'active', Workspace.mrr))
                        ),
                        0,
                    ).label('mrr'),
                ).where(Workspace.is_active == True)  # noqa: E712
            )
        ).one()

        mrr_float = round(float(row.mrr), 2)

        return {
            'active_subscriptions':      row.active,
            'total_revenue':             round(mrr_float * 12, 2),
            'monthly_recurring_revenue': mrr_float,
            'past_due':                  row.past_due,
            'trial_subscriptions':       row.trial,
        }


# ---------------------------------------------------------------------------
# Module-level helper functions (pure Python — kept sync)
# ---------------------------------------------------------------------------

def _calculate_growth_percentage(previous: int, current: int) -> str:
    """Return a human-readable growth percentage string."""
    if previous == 0:
        return '+100%' if current > 0 else '0%'
    growth = ((current - previous) / previous) * 100
    sign = '+' if growth >= 0 else ''
    return f'{sign}{growth:.1f}%'


def _get_time_ago(dt: datetime) -> str:
    """Convert a timezone-aware datetime to a human-readable 'X ago' string."""
    if not dt:
        return 'Unknown'

    try:
        # Ensure dt is timezone-aware; if naive, assume UTC.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        seconds = (now - dt).total_seconds()
    except (TypeError, AttributeError):
        return 'Unknown'

    if seconds < 60:
        return 'Just now'
    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(seconds / 86400)
    return f"{days} day{'s' if days != 1 else ''} ago"
