"""
System Dashboard Service
Provides analytics and statistics for system administrators
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from google.cloud import firestore

from src.config.Database import get_firestore_client
from src.system.services.Billing import BillingService


class SystemDashboardService:
    """Service for system-level dashboard data and analytics"""

    @staticmethod
    def get_system_stats() -> Dict[str, Any]:
        """Get overall system statistics"""
        db = get_firestore_client()
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)

        # Fetch all non-deleted workspaces once, then filter in Python
        # to avoid Firestore composite index requirements on compound queries
        workspaces_ref = db.collection('workspaces')
        all_workspaces = [
            doc.to_dict() for doc in workspaces_ref.where('is_deleted', '==', False).stream()
        ]

        total_workspaces = len(all_workspaces)

        active_workspaces = sum(
            1 for w in all_workspaces
            if w.get('updated_at') and w['updated_at'] >= thirty_days_ago
        )

        workspaces_last_30 = sum(
            1 for w in all_workspaces
            if w.get('created_at') and w['created_at'] >= thirty_days_ago
        )

        workspaces_prev_30 = sum(
            1 for w in all_workspaces
            if w.get('created_at') and sixty_days_ago <= w['created_at'] < thirty_days_ago
        )

        workspace_growth = calculate_growth_percentage(workspaces_prev_30, workspaces_last_30)

        # Fetch all non-deleted system users once
        system_users_ref = db.collection('system_users')
        all_system_users = [
            doc.to_dict() for doc in system_users_ref.where('is_deleted', '==', False).stream()
        ]

        total_system_users = len(all_system_users)

        active_system_users = sum(
            1 for u in all_system_users
            if u.get('last_login') and u['last_login'] >= thirty_days_ago
        )

        # Fetch all non-deleted application users once
        app_users_ref = db.collection('application_users')
        all_app_users = [
            doc.to_dict() for doc in app_users_ref.where('is_deleted', '==', False).stream()
        ]

        total_app_users = len(all_app_users)

        users_last_30 = sum(
            1 for u in all_app_users
            if u.get('created_at') and u['created_at'] >= thirty_days_ago
        )

        users_prev_30 = sum(
            1 for u in all_app_users
            if u.get('created_at') and sixty_days_ago <= u['created_at'] < thirty_days_ago
        )

        user_growth = calculate_growth_percentage(users_prev_30, users_last_30)

        # Total organizations
        orgs_ref = db.collection('organizations')
        total_organizations = len([doc for doc in orgs_ref.where('is_deleted', '==', False).stream()])

        return {
            "total_workspaces": total_workspaces,
            "active_workspaces": active_workspaces,
            "total_system_users": total_system_users,
            "active_system_users": active_system_users,
            "total_app_users": total_app_users,
            "total_organizations": total_organizations,
            "workspace_growth": workspace_growth,
            "user_growth": user_growth,
            "workspaces_last_30_days": workspaces_last_30,
            "users_last_30_days": users_last_30,
        }

    @staticmethod
    def get_workspace_growth_trend(days: int = 30) -> List[Dict[str, Any]]:
        """Get workspace growth trend over time"""
        db = get_firestore_client()
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Get all workspaces
        workspaces_ref = db.collection('workspaces')
        all_workspaces = [
            doc.to_dict() for doc in workspaces_ref
            .where('is_deleted', '==', False)
            .stream()
        ]

        # Group by date
        growth_data = []
        for i in range(days + 1):
            date = start_date + timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)

            count = sum(1 for w in all_workspaces if w.get('created_at') and w['created_at'] < date_end)

            growth_data.append({
                "date": date_start.strftime("%Y-%m-%d"),
                "period": date_start.strftime("%b %d"),
                "count": count
            })

        return growth_data

    @staticmethod
    def get_user_distribution() -> List[Dict[str, Any]]:
        """Get distribution of system users by role"""
        db = get_firestore_client()

        # Get all system users
        system_users_ref = db.collection('system_users')
        system_users = [
            doc.to_dict() for doc in system_users_ref
            .where('is_deleted', '==', False)
            .stream()
        ]

        # Get all roles
        roles_ref = db.collection('roles')
        roles = {doc.id: doc.to_dict() for doc in roles_ref.stream()}

        # Count users by role
        role_counts: Dict[str, int] = {}
        for user in system_users:
            role_id = user.get('role_id')
            if role_id and role_id in roles:
                role_name = roles[role_id].get('name', 'Unknown')
                role_counts[role_name] = role_counts.get(role_name, 0) + 1

        return [
            {"role": role_name, "count": count}
            for role_name, count in role_counts.items()
        ]

    @staticmethod
    def get_top_onboarders(limit: int = 5) -> List[Dict[str, Any]]:
        """Get system users who onboarded the most application users"""
        db = get_firestore_client()

        # Get all application users
        app_users_ref = db.collection('application_users')
        app_users = [
            doc.to_dict() for doc in app_users_ref
            .where('is_deleted', '==', False)
            .stream()
        ]

        # Count by created_by
        onboarder_counts: Dict[str, int] = {}
        for user in app_users:
            created_by = user.get('created_by')
            if created_by:
                onboarder_counts[created_by] = onboarder_counts.get(created_by, 0) + 1

        # Get system user details
        system_users_ref = db.collection('system_users')
        top_onboarders = []

        for user_id, count in sorted(onboarder_counts.items(), key=lambda x: x[1], reverse=True)[:limit]:
            user_doc = system_users_ref.document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
                if not name:
                    name = user_data.get('email', '').split('@')[0]

                top_onboarders.append({
                    "name": name,
                    "email": user_data.get('email', ''),
                    "users_onboarded": count
                })

        return top_onboarders

    @staticmethod
    def get_recent_activity(limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent system activity (last 24 hours)"""
        db = get_firestore_client()
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        activities = []

        # Fetch all non-deleted system users once, filter in Python
        # to avoid composite index on (is_deleted, last_login, order_by last_login)
        system_users_ref = db.collection('system_users')
        all_system_users = [
            doc.to_dict() for doc in system_users_ref.where('is_deleted', '==', False).stream()
        ]

        recent_logins = [
            u for u in all_system_users
            if u.get('last_login') and u['last_login'] >= twenty_four_hours_ago
        ]
        recent_logins.sort(key=lambda u: u['last_login'], reverse=True)

        for user in recent_logins[:10]:
            time_diff = get_time_ago(user['last_login'])
            activities.append({
                "id": f"login_{user.get('id', '')}",
                "type": "login",
                "user": user.get('email', ''),
                "action": "Logged in",
                "target": "",
                "time": time_diff,
                "timestamp": user['last_login'].isoformat() if isinstance(user['last_login'], datetime) else str(user['last_login'])
            })

        # Fetch all non-deleted workspaces, filter in Python
        # to avoid composite index on (is_deleted, created_at, order_by created_at)
        workspaces_ref = db.collection('workspaces')
        all_workspaces = [
            doc.to_dict() for doc in workspaces_ref.where('is_deleted', '==', False).stream()
        ]

        recent_workspaces = [
            w for w in all_workspaces
            if w.get('created_at') and w['created_at'] >= twenty_four_hours_ago
        ]
        recent_workspaces.sort(key=lambda w: w['created_at'], reverse=True)

        # Build a lookup map from the already-fetched system users
        system_users_map = {u.get('id', ''): u for u in all_system_users}

        for workspace in recent_workspaces[:10]:
            time_diff = get_time_ago(workspace['created_at'])

            creator_email = "System"
            created_by = workspace.get('created_by')
            if created_by:
                creator = system_users_map.get(created_by)
                if creator:
                    creator_email = creator.get('email', 'System')
                else:
                    # Fallback: fetch individually if not in the non-deleted set
                    creator_doc = system_users_ref.document(created_by).get()
                    if creator_doc.exists:
                        creator_email = creator_doc.to_dict().get('email', 'System')

            activities.append({
                "id": f"workspace_{workspace.get('id', '')}",
                "type": "workspace_created",
                "user": creator_email,
                "action": "Created new workspace",
                "target": workspace.get('name', ''),
                "time": time_diff,
                "timestamp": workspace['created_at'].isoformat() if isinstance(workspace['created_at'], datetime) else str(workspace['created_at'])
            })

        # Fetch all non-deleted application users, filter in Python
        # to avoid composite index on (is_deleted, created_at, order_by created_at)
        app_users_ref = db.collection('application_users')
        all_app_users = [
            doc.to_dict() for doc in app_users_ref.where('is_deleted', '==', False).stream()
        ]

        recent_app_users = [
            u for u in all_app_users
            if u.get('created_at') and u['created_at'] >= twenty_four_hours_ago
        ]
        recent_app_users.sort(key=lambda u: u['created_at'], reverse=True)

        for app_user in recent_app_users[:10]:
            time_diff = get_time_ago(app_user['created_at'])

            creator_email = "System"
            created_by = app_user.get('created_by')
            if created_by:
                creator = system_users_map.get(created_by)
                if creator:
                    creator_email = creator.get('email', 'System')
                else:
                    creator_doc = system_users_ref.document(created_by).get()
                    if creator_doc.exists:
                        creator_email = creator_doc.to_dict().get('email', 'System')

            activities.append({
                "id": f"user_{app_user.get('id', '')}",
                "type": "user_created",
                "user": creator_email,
                "action": "Created new user",
                "target": app_user.get('email', ''),
                "time": time_diff,
                "timestamp": app_user['created_at'].isoformat() if isinstance(app_user['created_at'], datetime) else str(app_user['created_at'])
            })

        # Sort all activities by timestamp and return top N
        activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return activities[:limit]

    @staticmethod
    def get_subscription_stats() -> Dict[str, Any]:
        """Get subscription and billing statistics"""
        db = get_firestore_client()

        # Get all workspaces
        workspaces_ref = db.collection('workspaces')
        workspaces = [
            doc.to_dict() for doc in workspaces_ref
            .where('is_deleted', '==', False)
            .stream()
        ]

        # Count subscriptions by status
        active_subscriptions = sum(1 for w in workspaces if w.get('subscription_status', '').lower() == 'active')
        past_due = sum(1 for w in workspaces if w.get('subscription_status', '').lower() == 'past due')
        trial_subscriptions = sum(1 for w in workspaces if w.get('subscription_status', '').lower() == 'trial')

        # Calculate MRR using BillingService.PLAN_PRICING
        monthly_recurring_revenue = 0.0

        for workspace in workspaces:
            if workspace.get('subscription_status', '').lower() == 'active':
                plan = workspace.get('subscription_plan', '').lower().strip()
                billing_cycle = workspace.get('billing_cycle', 'monthly').lower()

                # Find the best matching plan key
                matched_price = 0.0
                for plan_key, pricing in BillingService.PLAN_PRICING.items():
                    if plan_key in plan:
                        if billing_cycle == 'yearly':
                            # Normalise yearly price to monthly equivalent
                            matched_price = pricing.get('yearly', 0.0) / 12
                        else:
                            matched_price = pricing.get('monthly', 0.0)
                        break

                monthly_recurring_revenue += matched_price

        # Total revenue is MRR * 12 (annual estimate)
        total_revenue = monthly_recurring_revenue * 12

        return {
            "active_subscriptions": active_subscriptions,
            "total_revenue": round(total_revenue, 2),
            "monthly_recurring_revenue": round(monthly_recurring_revenue, 2),
            "past_due": past_due,
            "trial_subscriptions": trial_subscriptions
        }

    @staticmethod
    def get_registration_code_stats() -> Dict[str, Any]:
        """Get registration code statistics"""
        db = get_firestore_client()

        # Get all registration codes
        codes_ref = db.collection('registration_codes')
        all_codes = [
            doc.to_dict() for doc in codes_ref.stream()
        ]

        total_codes = len(all_codes)
        active_codes = sum(1 for c in all_codes if not c.get('is_deleted', False) and c.get('is_active', True))
        used_codes = sum(1 for c in all_codes if c.get('current_uses', 0) >= c.get('max_uses', 1))
        total_uses = sum(c.get('current_uses', 0) for c in all_codes)

        return {
            "total_codes": total_codes,
            "active_codes": active_codes,
            "used_codes": used_codes,
            "total_uses": total_uses
        }


def calculate_growth_percentage(previous: int, current: int) -> str:
    """Calculate growth percentage between two values"""
    if previous == 0:
        if current > 0:
            return "+100%"
        return "0%"

    growth = ((current - previous) / previous) * 100
    sign = "+" if growth >= 0 else ""
    return f"{sign}{growth:.1f}%"


def get_time_ago(dt: datetime) -> str:
    """Convert datetime to human-readable time ago string"""
    if not dt:
        return "Unknown"

    # Normalise to naive UTC for arithmetic — handles both Firestore
    # DatetimeWithNanoseconds (aware) and plain naive datetime objects.
    if hasattr(dt, 'timestamp'):
        # Works for both aware and naive datetime / Firestore timestamps
        dt = datetime.fromtimestamp(dt.timestamp(), tz=timezone.utc).replace(tzinfo=None)
    elif not isinstance(dt, datetime):
        return "Unknown"
    elif dt.tzinfo is not None:
        # Already an aware datetime — strip tzinfo after converting to UTC
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"