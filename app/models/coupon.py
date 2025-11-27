"""
Coupon Models
Data models for venue coupons and discount management
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


class DiscountType(str, Enum):
    """Discount type enumeration"""
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class CouponStatus(str, Enum):
    """Coupon status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"


class Coupon(BaseModel):
    """Coupon entity model"""
    id: str
    code: str = Field(..., description="Unique coupon code")
    venue_id: str = Field(..., description="Venue ID this coupon belongs to")
    workspace_id: str = Field(..., description="Workspace ID for isolation")
    
    # Discount configuration
    discount_type: DiscountType = Field(..., description="Type of discount (percentage or fixed)")
    discount_value: float = Field(..., gt=0, description="Discount value (percentage or rupees)")
    max_discount_amount: Optional[float] = Field(None, description="Maximum discount amount for percentage discounts")
    min_order_amount: Optional[float] = Field(None, description="Minimum order amount to apply coupon")
    
    # Validity
    expiry_date: datetime = Field(..., description="Coupon expiry date")
    is_active: bool = Field(default=True, description="Whether coupon is active")
    
    # Usage limits
    usage_limit: Optional[int] = Field(None, description="Maximum number of times coupon can be used")
    usage_count: int = Field(default=0, description="Number of times coupon has been used")
    per_user_limit: Optional[int] = Field(None, description="Maximum uses per user")
    
    # Metadata
    description: Optional[str] = Field(None, description="Coupon description")
    terms_and_conditions: Optional[str] = Field(None, description="Terms and conditions")
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = Field(None, description="User ID who created the coupon")
    
    @field_validator('discount_value')
    @classmethod
    def validate_discount_value(cls, v, info):
        """Validate discount value based on type"""
        discount_type = info.data.get('discount_type')
        
        if discount_type == DiscountType.PERCENTAGE:
            if v <= 0 or v > 100:
                raise ValueError("Percentage discount must be between 0 and 100")
        elif discount_type == DiscountType.FIXED:
            if v <= 0:
                raise ValueError("Fixed discount must be greater than 0")
        
        return v
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        """Validate coupon code format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Coupon code cannot be empty")
        
        # Convert to uppercase and remove spaces
        code = v.strip().upper()
        
        # Check length
        if len(code) < 3 or len(code) > 20:
            raise ValueError("Coupon code must be between 3 and 20 characters")
        
        # Check alphanumeric
        if not code.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Coupon code must be alphanumeric (hyphens and underscores allowed)")
        
        return code
    
    def is_expired(self) -> bool:
        """Check if coupon is expired"""
        return datetime.utcnow() > self.expiry_date
    
    def is_usage_limit_reached(self) -> bool:
        """Check if usage limit is reached"""
        if self.usage_limit is None:
            return False
        return self.usage_count >= self.usage_limit
    
    def can_be_used(self) -> bool:
        """Check if coupon can be used"""
        return (
            self.is_active and
            not self.is_expired() and
            not self.is_usage_limit_reached()
        )
    
    def get_status(self) -> CouponStatus:
        """Get current coupon status"""
        if self.is_expired():
            return CouponStatus.EXPIRED
        elif not self.is_active:
            return CouponStatus.INACTIVE
        else:
            return CouponStatus.ACTIVE


class CouponCreateDTO(BaseModel):
    """DTO for creating a coupon"""
    code: str = Field(..., min_length=3, max_length=20, description="Unique coupon code")
    venue_id: str = Field(..., description="Venue ID")
    
    # Discount configuration
    discount_type: DiscountType = Field(..., description="Type of discount")
    discount_value: float = Field(..., gt=0, description="Discount value")
    max_discount_amount: Optional[float] = Field(None, gt=0, description="Maximum discount amount")
    min_order_amount: Optional[float] = Field(None, gt=0, description="Minimum order amount")
    
    # Validity
    expiry_date: datetime = Field(..., description="Coupon expiry date")
    is_active: bool = Field(default=True, description="Active status")
    
    # Usage limits
    usage_limit: Optional[int] = Field(None, gt=0, description="Maximum uses")
    per_user_limit: Optional[int] = Field(None, gt=0, description="Maximum uses per user")
    
    # Metadata
    description: Optional[str] = Field(None, max_length=500)
    terms_and_conditions: Optional[str] = Field(None, max_length=2000)
    
    @field_validator('expiry_date')
    @classmethod
    def validate_expiry_date(cls, v):
        """Ensure expiry date is in the future"""
        if v <= datetime.utcnow():
            raise ValueError("Expiry date must be in the future")
        return v


class CouponUpdateDTO(BaseModel):
    """DTO for updating a coupon"""
    is_active: Optional[bool] = None
    expiry_date: Optional[datetime] = None
    usage_limit: Optional[int] = Field(None, gt=0)
    per_user_limit: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=500)
    terms_and_conditions: Optional[str] = Field(None, max_length=2000)
    
    @field_validator('expiry_date')
    @classmethod
    def validate_expiry_date(cls, v):
        """Ensure expiry date is in the future"""
        if v and v <= datetime.utcnow():
            raise ValueError("Expiry date must be in the future")
        return v


class CouponResponseDTO(BaseModel):
    """DTO for coupon response"""
    id: str
    code: str
    venue_id: str
    workspace_id: str
    discount_type: DiscountType
    discount_value: float
    max_discount_amount: Optional[float]
    min_order_amount: Optional[float]
    expiry_date: datetime
    is_active: bool
    status: CouponStatus
    usage_limit: Optional[int]
    usage_count: int
    per_user_limit: Optional[int]
    description: Optional[str]
    terms_and_conditions: Optional[str]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]


class ApplyCouponRequest(BaseModel):
    """Request to apply a coupon"""
    coupon_code: str = Field(..., description="Coupon code to apply")
    venue_id: str = Field(..., description="Venue ID")
    order_amount: float = Field(..., gt=0, description="Order amount before discount")
    user_id: Optional[str] = Field(None, description="User ID for per-user limit check")


class ApplyCouponResponse(BaseModel):
    """Response after applying a coupon"""
    success: bool
    message: str
    coupon_code: str
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = None
    discount_amount: Optional[float] = None
    original_amount: Optional[float] = None
    final_amount: Optional[float] = None
    savings: Optional[float] = None
    coupon_details: Optional[CouponResponseDTO] = None