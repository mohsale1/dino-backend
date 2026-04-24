"""
SystemDashboardService — analytics and statistics for system administrators.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.Persona import Persona
from src.models.Role import Role
from src.models.User import User
from src.models.Workspace import Workspace
from src.models.WorkspaceBilling import WorkspaceBilling


class SystemDashboardService:
    """Service for system-level dashboard data and analytics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_system_stats(self) -> Dict[str, Any]:
        """Return overall system statistics."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        # Workspace counts
        ws_row = (
            await self.db.execute(
                select(
                    func.count().label("total"),
                    func.count(case((Workspace.is_active == True, 1))).label("active"),  # noqa: E712
                    func.count(case((Workspace.created_at >= thirty_days_ago, 1))).label("last_30"),
                    func.count(case((
                        and_(
                            Workspace.created_at >= sixty_days_ago,
                            Workspace.created_at < thirty_days_ago,
                        ), 1,
                    ))).label("prev_30"),
                )
            )
        ).one()

        # System user counts (user_type=0)
        sys_user_row = (
            await self.db.execute(
                select(
                    func.count().label("total"),
                    func.count(case((User.last_login >= thirty_days_ago, 1))).label("active"),
                ).where(User.user_type == 0, User.is_active == True)  # noqa: E712
            )
        ).one()

        # Application user counts (user_type=1)
        app_user_row = (
            await self.db.execute(
                select(func.count().label("total"))
                .where(User.user_type == 1, User.is_active == True)  # noqa: E712
            )
        ).one()

        # Persona count
        total_personas: int = (
            await self.db.execute(
                select(func.count()).select_from(Persona).where(Persona.is_active == True)  # noqa: E712
            )
        ).scalar_one()

        workspace_growth = _calculate_growth_percentage(ws_row.prev_30, ws_row.last_30)

        return {
            "total_workspaces": ws_row.total,
            "active_workspaces": ws_row.active,
            "total_system_users": sys_user_row.total,
            "active_system_users": sys_user_row.active,
            "total_app_users": app_user_row.total,
            "total_personas": total_personas,
            "workspace_growth": workspace_growth,
            "workspaces_last_30_days": ws_row.last_30,
        }

    async def get_workspace_growth(self, days: int = 30) -> List[Dict[str, Any]]:
        """Return workspace creation counts per day for the last N days."""
        from sqlalchemy import text as _text

        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        stmt = _text(
            "SELECT DATE(created_at) AS day, COUNT(*) AS count "
            "FROM workspaces "
            "WHERE created_at >= :start "
            "GROUP BY DATE(created_at) "
            "ORDER BY day"
        )
        result = await self.db.execute(stmt, {"start": start_date})
        rows = result.all()

        # Build a lookup: date string -> count
        counts_by_day: Dict[str, int] = {
            str(row.day): int(row.count) for row in rows
        }

        # Fill every day in the range (including days with 0 workspaces)
        growth_data: List[Dict[str, Any]] = []
        for i in range(days + 1):
            day_dt = start_date + timedelta(days=i)
            day_str = day_dt.strftime("%Y-%m-%d")
            growth_data.append({
                "date": day_str,
                "period": day_dt.strftime("%b %d"),
                "count": counts_by_day.get(day_str, 0),
            })

        return growth_data



    async def get_user_distribution(self) -> List[Dict[str, Any]]:
        """Return user counts grouped by role name."""
        stmt = (
            select(Role.name, func.count(User.id).label("count"))
            .join(Role, User.role_id == Role.id)
            .where(User.is_active == True)  # noqa: E712
            .group_by(Role.name)
        )
        result = await self.db.execute(stmt)
        return [{"role": row.name, "count": row.count} for row in result.all()]

    async def get_billing_overview(self) -> Dict[str, Any]:
        """Return workspaces by plan and revenue summary from billing_transactions."""

        plan_stmt = (
            select(WorkspaceBilling.plan, func.count().label("count"))
            .group_by(WorkspaceBilling.plan)
        )
        plan_result = await self.db.execute(plan_stmt)
        by_plan = {row.plan: row.count for row in plan_result.all()}

        status_stmt = (
            select(WorkspaceBilling.plan_status, func.count().label("count"))
            .group_by(WorkspaceBilling.plan_status)
        )
        status_result = await self.db.execute(status_stmt)
        by_status = {row.plan_status: row.count for row in status_result.all()}

        return {
            "by_plan": by_plan,
            "by_status": by_status,
        }

    async def get_recent_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent workspace creations and user logins."""
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        activities: List[Dict[str, Any]] = []

        # Recent user logins
        login_stmt = (
            select(User.id, User.email, User.last_login)
            .where(
                and_(
                    User.is_active == True,  # noqa: E712
                    User.last_login >= twenty_four_hours_ago,
                )
            )
            .order_by(User.last_login.desc())
            .limit(10)
        )
        for row in (await self.db.execute(login_stmt)).all():
            activities.append({
                "id": f"login_{row.id}",
                "type": "login",
                "user": row.email,
                "action": "Logged in",
                "target": "",
                "time": _get_time_ago(row.last_login),
                "timestamp": row.last_login.isoformat() if row.last_login else "",
            })

        # Recently created workspaces
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
        for row in (await self.db.execute(ws_stmt)).all():
            activities.append({
                "id": f"workspace_{row.id}",
                "type": "workspace_created",
                "user": "System",
                "action": "Created new workspace",
                "target": row.name,
                "time": _get_time_ago(row.created_at),
                "timestamp": row.created_at.isoformat() if row.created_at else "",
            })

        activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return activities[:limit]

    async def get_referral_overview(self, days: int = 30) -> Dict[str, Any]:
        """Return full referral statistics sourced from workspace_requests."""
        from src.repositories.WorkspaceRequestRepository import WorkspaceRequestRepository

        repo = WorkspaceRequestRepository(self.db)
        raw = await repo.get_referral_stats(days=days)

        summary_row = raw["summary_row"]
        top_referrers = raw["top_referrers"]

        growth = _calculate_growth_percentage(summary_row.prev_n_days, summary_row.last_n_days)

        return {
            "summary": {
                "total_referrals": summary_row.total,
                "total_referrers": summary_row.total_referrers,
                "pending": summary_row.pending,
                "approved": summary_row.approved,
                "rejected": summary_row.rejected,
                f"referrals_last_{days}_days": summary_row.last_n_days,
                "referral_growth": growth,
                "period_days": days,
            },
            "top_referrers": top_referrers,
        }

    async def get_top_workspaces(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return workspaces with most personas and users."""
        persona_count_sq = (
            select(func.count())
            .select_from(Persona)
            .where(
                Persona.workspace_id == Workspace.id,
                Persona.is_active == True,  # noqa: E712
            )
            .correlate(Workspace)
            .scalar_subquery()
        )
        user_count_sq = (
            select(func.count())
            .select_from(User)
            .where(
                User.workspace_id == Workspace.id,
                User.is_active == True,  # noqa: E712
            )
            .correlate(Workspace)
            .scalar_subquery()
        )
        stmt = (
            select(
                Workspace.id,
                Workspace.name,
                Workspace.created_at,
                persona_count_sq.label("persona_count"),
                user_count_sq.label("user_count"),
            )
            .where(Workspace.is_active == True)  # noqa: E712
            .order_by(Workspace.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "id": row.id,
                "name": row.name,
                "persona_count": row.persona_count,
                "user_count": row.user_count,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in result.all()
        ]



# ---------------------------------------------------------------------------
# Module-level helper functions
# ---------------------------------------------------------------------------

def _calculate_growth_percentage(previous: int, current: int) -> str:
    if previous == 0:
        return "+100%" if current > 0 else "0%"
    growth = ((current - previous) / previous) * 100
    sign = "+" if growth >= 0 else ""
    return f"{sign}{growth:.1f}%"


def _get_time_ago(dt: datetime) -> str:
    if not dt:
        return "Unknown"
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        seconds = (now - dt).total_seconds()
    except (TypeError, AttributeError):
        return "Unknown"

    if seconds < 60:
        return "Just now"
    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(seconds / 86400)
    return f"{days} day{'s' if days != 1 else ''} ago"
