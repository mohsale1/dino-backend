from src.base.BaseModel import BaseModel
from typing import Optional
from datetime import datetime

class Coupon(BaseModel):
    """Coupon model - represents discount coupons"""
    
    def __init__(self):
        super().__init__()
        self.code: str = ""  # Unique coupon code
        self.name: str = ""  # Display name
        self.description: Optional[str] = None
        self.workspace_id: str = ""  # Belongs to a workspace
        
        # Discount details
        self.discount_type: str = "percentage"  # percentage, fixed
        self.discount_value: float = 0.0  # Percentage (0-100) or fixed amount
        self.max_discount_amount: Optional[float] = None  # Max discount for percentage type
        self.min_order_amount: Optional[float] = None  # Minimum order amount to apply
        
        # Usage limits
        self.usage_limit: Optional[int] = None  # Total usage limit (None = unlimited)
        self.usage_count: int = 0  # Current usage count
        self.usage_limit_per_user: Optional[int] = None  # Per user limit
        
        # Validity
        self.valid_from: Optional[datetime] = None
        self.valid_until: Optional[datetime] = None
        
        # Status
        self.is_available: bool = True