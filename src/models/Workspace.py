from src.base.BaseModel import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class Workspace(BaseModel):
    """Workspace model - contains multiple organizations (venues/branches)"""
    
    def __init__(self):
        super().__init__()
        self.name: str = ""  # e.g., "McDonald's Franchise"
        self.description: Optional[str] = None
        self.organization_ids: List[str] = []  # List of organizations under this workspace
        
        # Workspace owner/admin (reference only - details fetched from user)
        self.owner_id: str = ""
        
        # Referral tracking - who onboarded this workspace (4-digit system user ID)
        self.referred_by: Optional[str] = None
        
        # Billing Contact Information
        self.billing_name: Optional[str] = None
        self.billing_email: Optional[str] = None
        self.billing_phone: Optional[str] = None
        self.billing_address: Optional[str] = None
        self.billing_city: Optional[str] = None
        self.billing_state: Optional[str] = None
        self.billing_postal_code: Optional[str] = None
        self.billing_country: Optional[str] = None
        
        # Subscription Information
        self.subscription_plan: str = "Free"  # Free, Basic, Standard, Premium, Pro, Enterprise
        self.subscription_status: str = "Active"  # Active, Trial, Past Due, Cancelled, Inactive
        self.billing_cycle: str = "Monthly"  # Monthly, Yearly
        self.payment_method: Optional[str] = None  # Credit Card, PayPal, Bank Transfer, etc.
        self.currency: str = "USD"
        
        # Billing Dates
        self.subscription_start_date: Optional[datetime] = None
        self.next_billing_date: Optional[datetime] = None
        self.last_billing_date: Optional[datetime] = None
        self.trial_end_date: Optional[datetime] = None
        
        # Billing Amounts
        self.monthly_amount: float = 0.0
        self.yearly_amount: float = 0.0
        
        # Additional Billing Info
        self.billing_info: Dict[str, Any] = {}  # Additional billing metadata
        self.auto_renew: bool = True
        self.payment_failed_count: int = 0
