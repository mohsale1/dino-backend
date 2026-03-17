"""
System Dashboard Service
Provides analytics and statistics for system administrators
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from google.cloud import firestore

from src.config.Database import get_firestore_client


class SystemDashboardService:
    """Service for system-level dashboard data and analytics"""
    
    @staticmethod
    def get_system_stats() -> Dict[str, Any]:
        """Get overall system statistics"""
        db = get_firestore_client()
        
        # Total workspaces
        workspaces_ref = db.collection('workspaces')
        total_workspaces = len([doc for doc in workspaces_ref.where('is_deleted', '==', False).stream()])
        
        # Active workspaces (with recent activity - last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_workspaces = len([
            doc for doc in workspaces_ref
            .where('is_deleted', '==', False)
            .where('updated_at', '>=', thirty_days_ago)
            .stream()
        ])
        
        # Total system users
        system_users_ref = db.collection('system_users')
        total_system_users = len([doc for doc in system_users_ref.where('is_deleted', '==', False).stream()])
        
        # Active system users (logged in last 30 days)
        active_system_users = len([
            doc for doc in system_users_ref
            .where('is_deleted', '==', False)
            .where('last_login', '>=', thirty_days_ago)
            .stream()
        ])
        
        # Total application users
        app_users_ref = db.collection('application_users')
        total_app_users = len([doc for doc in app_users_ref.where('is_deleted', '==', False).stream()])
        
        # Total organizations
        orgs_ref = db.collection('organizations')
        total_organizations = len([doc for doc in orgs_ref.where('is_deleted', '==', False).stream()])
        
        # Calculate growth rates (last 30 days vs previous 30 days)
        sixty_days_ago = datetime.utcnow() - timedelta(days=60)
        
        # Workspace growth
        workspaces_last_30 = len([
            doc for doc in workspaces_ref
            .where('is_deleted', '==', False)
            .where('created_at', '>=', thirty_days_ago)
            .stream()
        ])
        
        workspaces_prev_30 = len([
            doc for doc in workspaces_ref
            .where('is_deleted', '==', False)
            .where('created_at', '>=', sixty_days_ago)
            .where('created_at', '<', thirty_days_ago)
            .stream()
        ])
        
        workspace_growth = calculate_growth_percentage(workspaces_prev_30, workspaces_last_30)
        
        # User growth
        users_last_30 = len([
            doc for doc in app_users_ref
            .where('is_deleted', '==', False)
            .where('created_at', '>=', thirty_days_ago)
            .stream()
        ])
        
        users_prev_30 = len([
            doc for doc in app_users_ref
            .where('is_deleted', '==', False)
            .where('created_at', '>=', sixty_days_ago)
            .where('created_at', '<', thirty_days_ago)
            .stream()
        ])
        
        user_growth = calculate_growth_percentage(users_prev_30, users_last_30)
        
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
        start_date = datetime.utcnow() - timedelta(days=days)
        
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
            
            # Count workspaces created before this date
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
        role_counts = {}
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
        onboarder_counts = {}
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
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        activities = []
        
        # Recent system user logins
        system_users_ref = db.collection('system_users')
        recent_logins = [
            doc.to_dict() for doc in system_users_ref
            .where('is_deleted', '==', False)
            .where('last_login', '>=', twenty_four_hours_ago)
            .order_by('last_login', direction=firestore.Query.DESCENDING)
            .limit(10)
            .stream()
        ]
        
        for user in recent_logins:
            if user.get('last_login'):
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
        
        # Recent workspace creations
        workspaces_ref = db.collection('workspaces')
        recent_workspaces = [
            doc.to_dict() for doc in workspaces_ref
            .where('is_deleted', '==', False)
            .where('created_at', '>=', twenty_four_hours_ago)
            .order_by('created_at', direction=firestore.Query.DESCENDING)
            .limit(10)
            .stream()
        ]
        
        for workspace in recent_workspaces:
            if workspace.get('created_at'):
                time_diff = get_time_ago(workspace['created_at'])
                
                # Get creator info
                creator_email = "System"
                if workspace.get('created_by'):
                    creator_doc = system_users_ref.document(workspace['created_by']).get()
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
        
        # Recent application user creations
        app_users_ref = db.collection('application_users')
        recent_app_users = [
            doc.to_dict() for doc in app_users_ref
            .where('is_deleted', '==', False)
            .where('created_at', '>=', twenty_four_hours_ago)
            .order_by('created_at', direction=firestore.Query.DESCENDING)
            .limit(10)
            .stream()
        ]
        
        for app_user in recent_app_users:
            if app_user.get('created_at'):
                time_diff = get_time_ago(app_user['created_at'])
                
                # Get creator info
                creator_email = "System"
                if app_user.get('created_by'):
                    creator_doc = system_users_ref.document(app_user['created_by']).get()
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
        
        # Sort all activities by timestamp
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
        
        # Calculate revenue (basic calculation based on plan)
        total_revenue = 0
        monthly_recurring_revenue = 0
        
        for workspace in workspaces:
            if workspace.get('subscription_status', '').lower() == 'active':
                plan = workspace.get('subscription_plan', '').lower()
                if 'premium' in plan or 'pro' in plan:
                    monthly_recurring_revenue += 99
                elif 'standard' in plan or 'basic' in plan:
                    monthly_recurring_revenue += 49
                elif 'enterprise' in plan:
                    monthly_recurring_revenue += 199
        
        # Total revenue is MRR * 12 (annual estimate)
        total_revenue = monthly_recurring_revenue * 12
        
        return {
            "active_subscriptions": active_subscriptions,
            "total_revenue": total_revenue,
            "monthly_recurring_revenue": monthly_recurring_revenue,
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
        
        # Count codes by status
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
    
    # Handle Firestore timestamp
    if hasattr(dt, 'timestamp'):
        dt = datetime.fromtimestamp(dt.timestamp())
    elif not isinstance(dt, datetime):
        return "Unknown"
    
    now = datetime.utcnow()
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