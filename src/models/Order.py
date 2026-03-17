from src.base.BaseModel import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

class Order(BaseModel):
    """Order model"""
    
    def __init__(self):
        super().__init__()
        self.order_number: str = ""
        self.workspace_id: str = ""
        self.organization_id: str = ""
        
        # Order type and source
        self.order_type: int = 0  # 0 = Online, 1 = Manual (Counter)
        self.table_id: Optional[str] = None
        self.area_id: Optional[str] = None
        
        # Customer information
        self.customer_name: Optional[str] = None
        self.customer_email: Optional[str] = None
        self.customer_phone: Optional[str] = None
        self.guest_count: Optional[int] = None
        
        # Order details
        self.items: List[Dict[str, Any]] = []
        self.subtotal: float = 0.0
        self.tax_amount: float = 0.0
        self.discount_amount: float = 0.0
        self.service_charge: float = 0.0
        self.total_amount: float = 0.0
        self.currency: str = "USD"
        
        # Status tracking
        self.status: str = "pending"  # pending, confirmed, preparing, ready, served, completed, cancelled
        self.payment_status: str = "unpaid"  # unpaid, partial, paid, refunded
        self.payment_method: Optional[str] = None  # cash, card, upi, wallet
        
        # Additional information
        self.special_instructions: Optional[str] = None
        self.notes: Optional[str] = None
        self.order_date: datetime = datetime.now(timezone.utc)
        self.confirmed_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.cancelled_at: Optional[datetime] = None
        
        # Staff information
        self.created_by: Optional[str] = None  # User ID who created the order
        self.served_by: Optional[str] = None  # User ID who served the order
