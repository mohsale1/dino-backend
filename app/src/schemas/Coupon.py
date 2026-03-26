from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CouponBase(BaseModel):
    """Base coupon schema"""
    code: str = Field(..., min_length=3, max_length=50, description="Unique coupon code")
    name: str = Field(..., min_length=1, max_length=200, description="Display name")
    description: Optional[str] = Field(None, max_length=500)
    discount_type: str = Field(..., pattern="^(percentage|fixed)$", description="Discount type: percentage or fixed")
    discount_value: float = Field(..., gt=0, description="Discount value (percentage 0-100 or fixed amount)")
    max_discount_amount: Optional[float] = Field(None, ge=0, description="Maximum discount amount for percentage type")
    min_order_amount: Optional[float] = Field(None, ge=0, description="Minimum order amount required")
    usage_limit: Optional[int] = Field(None, ge=1, description="Total usage limit")
    usage_limit_per_user: Optional[int] = Field(None, ge=1, description="Usage limit per user")
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_available: bool = True

class CouponCreate(CouponBase):
    """Create coupon schema"""
    workspace_id: str = Field(..., description="Workspace ID")

class CouponUpdate(BaseModel):
    """Update coupon schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    discount_type: Optional[str] = Field(None, pattern="^(percentage|fixed)$")
    discount_value: Optional[float] = Field(None, gt=0)
    max_discount_amount: Optional[float] = Field(None, ge=0)
    min_order_amount: Optional[float] = Field(None, ge=0)
    usage_limit: Optional[int] = Field(None, ge=1)
    usage_limit_per_user: Optional[int] = Field(None, ge=1)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_available: Optional[bool] = None

class CouponResponse(CouponBase):
    """Coupon response schema"""
    id: str
    workspace_id: str
    usage_count: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True