from src.base.BaseService import BaseService
from src.repositories.WorkspaceRepository import WorkspaceRepository
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

class BillingService(BaseService):
    """Billing service"""
    
    # Plan pricing configuration
    PLAN_PRICING = {
        'free': {'monthly': 0.0, 'yearly': 0.0},
        'basic': {'monthly': 49.0, 'yearly': 490.0},
        'standard': {'monthly': 99.0, 'yearly': 990.0},
        'premium': {'monthly': 149.0, 'yearly': 1490.0},
        'pro': {'monthly': 199.0, 'yearly': 1990.0},
        'enterprise': {'monthly': 299.0, 'yearly': 2990.0},
    }
    
    def __init__(self):
        repository = WorkspaceRepository()
        super().__init__(repository)
    
    def _get_plan_amount(self, plan: str, billing_cycle: str = 'Monthly') -> float:
        """Get amount for a subscription plan based on billing cycle"""
        if not plan:
            return 0.0
        
        plan_lower = plan.lower()
        cycle_key = 'yearly' if billing_cycle.lower() == 'yearly' else 'monthly'
        
        # Find matching plan
        for plan_name, pricing in self.PLAN_PRICING.items():
            if plan_name in plan_lower:
                return pricing[cycle_key]
        
        return 0.0
    
    def _calculate_next_billing_date(self, workspace: Dict[str, Any]) -> str:
        """Calculate next billing date based on subscription status and billing cycle"""
        subscription_status = workspace.get('subscription_status', '').lower()
        
        # If subscription is not active or trial, return None
        if subscription_status not in ['active', 'trial']:
            return None
        
        now = datetime.now(timezone.utc)

        # Check if next_billing_date is already set and in the future
        existing_next_billing = workspace.get('next_billing_date')
        if existing_next_billing:
            try:
                if isinstance(existing_next_billing, str):
                    next_billing_dt = datetime.fromisoformat(existing_next_billing.replace('Z', '+00:00'))
                else:
                    next_billing_dt = existing_next_billing
                
                # Ensure aware datetime for comparison
                if next_billing_dt.tzinfo is None:
                    next_billing_dt = next_billing_dt.replace(tzinfo=timezone.utc)

                # If it's in the future, return it
                if next_billing_dt > now:
                    return next_billing_dt.isoformat()
            except (ValueError, TypeError, AttributeError):
                pass
        
        # Calculate based on subscription_start_date or created_at
        start_date = workspace.get('subscription_start_date') or workspace.get('created_at')
        billing_cycle = workspace.get('billing_cycle', 'Monthly')
        
        if start_date:
            if isinstance(start_date, str):
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except (ValueError, TypeError, AttributeError):
                    start_dt = now
            else:
                start_dt = start_date
            
            # Ensure aware datetime for comparison
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)

            # Calculate billing interval
            if billing_cycle.lower() == 'yearly':
                days_interval = 365
            else:  # Monthly
                days_interval = 30
            
            # Calculate next billing date
            next_billing = start_dt + timedelta(days=days_interval)
            
            # If next billing is in the past, calculate the next future billing date
            while next_billing < now:
                next_billing += timedelta(days=days_interval)
            
            return next_billing.isoformat()
        
        # Default to 30 days from now for monthly, 365 for yearly
        days = 365 if billing_cycle.lower() == 'yearly' else 30
        return (now + timedelta(days=days)).isoformat()
    
    def get_workspace_billing(self, workspace_id: str) -> Dict[str, Any]:
        """Get workspace billing information"""
        workspace = self.get_by_id(workspace_id)
        
        if not workspace:
            return None
        
        subscription_plan = workspace.get('subscription_plan', 'Free')
        billing_cycle = workspace.get('billing_cycle', 'Monthly')
        next_billing_date = self._calculate_next_billing_date(workspace)
        amount = self._get_plan_amount(subscription_plan, billing_cycle)
        
        return {
            "workspace_id": workspace.get('id'),
            "workspace_name": workspace.get('name'),
            
            # Subscription Details
            "subscription_plan": subscription_plan,
            "subscription_status": workspace.get('subscription_status', 'Active'),
            "billing_cycle": billing_cycle,
            
            # Billing Contact
            "billing_email": workspace.get('billing_email'),
            "billing_address": workspace.get('billing_address'),
            
            # Payment Details
            "payment_method": workspace.get('payment_method', 'Not Set'),
            "currency": workspace.get('currency', 'USD'),
            "amount": amount,
            "monthly_amount": workspace.get('monthly_amount', self._get_plan_amount(subscription_plan, 'Monthly')),
            "yearly_amount": workspace.get('yearly_amount', self._get_plan_amount(subscription_plan, 'Yearly')),
            
            # Billing Dates
            "subscription_start_date": workspace.get('subscription_start_date'),
            "next_billing_date": next_billing_date,
            "last_billing_date": workspace.get('last_billing_date'),
            "trial_end_date": workspace.get('trial_end_date'),
            
            # Additional Info
            "auto_renew": workspace.get('auto_renew', True),
            "payment_failed_count": workspace.get('payment_failed_count', 0),
            "billing_info": workspace.get('billing_info', {})
        }
    
    def update_subscription(self, workspace_id: str, plan: str, status: str) -> bool:
        """Update workspace subscription and recalculate billing"""
        workspace = self.get_by_id(workspace_id)
        if not workspace:
            return False
        
        billing_cycle = workspace.get('billing_cycle', 'Monthly')
        
        # Calculate amounts based on new plan
        monthly_amount = self._get_plan_amount(plan, 'Monthly')
        yearly_amount = self._get_plan_amount(plan, 'Yearly')
        
        update_data = {
            "subscription_plan": plan,
            "subscription_status": status,
            "monthly_amount": monthly_amount,
            "yearly_amount": yearly_amount,
        }
        
        # If changing to active status and no start date, set it
        if status.lower() == 'active' and not workspace.get('subscription_start_date'):
            update_data['subscription_start_date'] = datetime.now(timezone.utc).isoformat()
        
        # Recalculate next billing date
        workspace_updated = {**workspace, **update_data}
        next_billing = self._calculate_next_billing_date(workspace_updated)
        if next_billing:
            update_data['next_billing_date'] = next_billing
        
        return self.update(workspace_id, update_data)
    
    def update_billing_cycle(self, workspace_id: str, billing_cycle: str) -> bool:
        """Update billing cycle and recalculate next billing date"""
        workspace = self.get_by_id(workspace_id)
        if not workspace:
            return False
        
        update_data = {
            "billing_cycle": billing_cycle
        }
        
        # Recalculate next billing date based on new cycle
        workspace_updated = {**workspace, **update_data}
        next_billing = self._calculate_next_billing_date(workspace_updated)
        if next_billing:
            update_data['next_billing_date'] = next_billing
        
        return self.update(workspace_id, update_data)
    
    def process_billing(self, workspace_id: str) -> Dict[str, Any]:
        """Process billing for a workspace (called on billing date)"""
        workspace = self.get_by_id(workspace_id)
        if not workspace:
            return {"success": False, "message": "Workspace not found"}
        
        subscription_plan = workspace.get('subscription_plan', 'Free')
        billing_cycle = workspace.get('billing_cycle', 'Monthly')
        amount = self._get_plan_amount(subscription_plan, billing_cycle)
        
        now = datetime.now(timezone.utc)

        # Update last billing date and calculate next billing date
        update_data = {
            "last_billing_date": now.isoformat()
        }
        
        # Calculate next billing date
        if billing_cycle.lower() == 'yearly':
            next_billing = now + timedelta(days=365)
        else:
            next_billing = now + timedelta(days=30)
        
        update_data['next_billing_date'] = next_billing.isoformat()
        
        # Reset payment failed count on successful billing
        update_data['payment_failed_count'] = 0
        
        self.update(workspace_id, update_data)
        
        return {
            "success": True,
            "message": "Billing processed successfully",
            "amount": amount,
            "currency": workspace.get('currency', 'USD'),
            "next_billing_date": next_billing.isoformat()
        }
    
    def get_all_billing_info(self) -> List[Dict[str, Any]]:
        """Get billing information for all workspaces"""
        workspaces = self.get_all()
        
        return [
            {
                "workspace_id": ws.get('id'),
                "workspace_name": ws.get('name'),
                "billing_email": ws.get('billing_email'),
                "subscription_plan": ws.get('subscription_plan', 'Free'),
                "subscription_status": ws.get('subscription_status', 'Active'),
                "next_billing_date": self._calculate_next_billing_date(ws),
                "amount": self._get_plan_amount(ws.get('subscription_plan', 'Free'), ws.get('billing_cycle', 'Monthly'))
            }
            for ws in workspaces
        ]
    
    def get_paginated_billing_info(
        self,
        page: int = 1,
        page_size: int = 10,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ):
        """Get paginated billing information for all workspaces"""
        items, total, total_pages = self.get_paginated(
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_direction=order_direction
        )
        
        billing_info = [
            {
                "workspace_id": ws.get('id'),
                "workspace_name": ws.get('name'),
                "billing_email": ws.get('billing_email'),
                "subscription_plan": ws.get('subscription_plan', 'Free'),
                "subscription_status": ws.get('subscription_status', 'Active'),
                "billing_cycle": ws.get('billing_cycle', 'Monthly'),
                "next_billing_date": self._calculate_next_billing_date(ws),
                "last_billing_date": ws.get('last_billing_date'),
                "payment_method": ws.get('payment_method', 'Not Set'),
                "amount": self._get_plan_amount(ws.get('subscription_plan', 'Free'), ws.get('billing_cycle', 'Monthly')),
                "currency": ws.get('currency', 'USD'),
                "auto_renew": ws.get('auto_renew', True),
                "payment_failed_count": ws.get('payment_failed_count', 0),
                "billing_info": ws.get('billing_info', {}),
                "created_at": ws.get('created_at')
            }
            for ws in items
        ]
        
        return billing_info, total, total_pages
    
    def get_billing_stats(self) -> Dict[str, Any]:
        """Get billing statistics"""
        workspaces = self.get_all()
        
        total_subscriptions = len(workspaces)
        active_subscriptions = sum(1 for ws in workspaces if ws.get('subscription_status', '').lower() == 'active')
        trial_subscriptions = sum(1 for ws in workspaces if ws.get('subscription_status', '').lower() == 'trial')
        past_due = sum(1 for ws in workspaces if ws.get('subscription_status', '').lower() == 'past due')
        cancelled = sum(1 for ws in workspaces if ws.get('subscription_status', '').lower() == 'cancelled')
        
        # Calculate monthly revenue (only from active subscriptions)
        monthly_revenue = 0.0
        yearly_revenue = 0.0
        
        for ws in workspaces:
            if ws.get('subscription_status', '').lower() == 'active':
                billing_cycle = ws.get('billing_cycle', 'Monthly')
                plan = ws.get('subscription_plan', 'Free')
                
                if billing_cycle.lower() == 'yearly':
                    yearly_revenue += self._get_plan_amount(plan, 'Yearly')
                    # Convert to monthly equivalent
                    monthly_revenue += self._get_plan_amount(plan, 'Yearly') / 12
                else:
                    monthly_revenue += self._get_plan_amount(plan, 'Monthly')
        
        now = datetime.now(timezone.utc)

        # Calculate total invoices (estimate based on subscription age)
        total_invoices = 0
        for ws in workspaces:
            start_date = ws.get('subscription_start_date') or ws.get('created_at')
            if start_date:
                if isinstance(start_date, str):
                    try:
                        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    except (ValueError, TypeError, AttributeError):
                        start_dt = now
                else:
                    start_dt = start_date
                
                # Ensure aware datetime for subtraction
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)

                # Calculate months since start
                months_active = max(1, int((now - start_dt).days / 30))
                
                # If yearly billing, count as 1 invoice per year
                if ws.get('billing_cycle', 'Monthly').lower() == 'yearly':
                    total_invoices += max(1, months_active // 12)
                else:
                    total_invoices += months_active
        
        return {
            "total_subscriptions": total_subscriptions,
            "active_subscriptions": active_subscriptions,
            "trial_subscriptions": trial_subscriptions,
            "past_due": past_due,
            "cancelled": cancelled,
            "monthly_revenue": round(monthly_revenue, 2),
            "yearly_revenue": round(yearly_revenue, 2),
            "total_invoices": total_invoices,
            "average_revenue_per_user": round(monthly_revenue / max(1, active_subscriptions), 2)
        }
    
    def get_upcoming_renewals(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get workspaces with upcoming billing renewals"""
        workspaces = self.get_all()
        upcoming = []
        
        now = datetime.now(timezone.utc)
        cutoff_date = now + timedelta(days=days)
        
        for ws in workspaces:
            if ws.get('subscription_status', '').lower() != 'active':
                continue
            
            next_billing = self._calculate_next_billing_date(ws)
            if next_billing:
                try:
                    next_billing_dt = datetime.fromisoformat(next_billing.replace('Z', '+00:00'))

                    # Ensure aware datetime for comparison
                    if next_billing_dt.tzinfo is None:
                        next_billing_dt = next_billing_dt.replace(tzinfo=timezone.utc)

                    if now <= next_billing_dt <= cutoff_date:
                        upcoming.append({
                            "workspace_id": ws.get('id'),
                            "workspace_name": ws.get('name'),
                            "next_billing_date": next_billing,
                            "amount": self._get_plan_amount(ws.get('subscription_plan', 'Free'), ws.get('billing_cycle', 'Monthly')),
                            "currency": ws.get('currency', 'USD'),
                            "billing_email": ws.get('billing_email')
                        })
                except (ValueError, TypeError, AttributeError):
                    pass
        
        return upcoming