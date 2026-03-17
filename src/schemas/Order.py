from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class OrderItemSchema(BaseModel):
    """Order item schema"""
    product_id: str
    product_name: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    total_price: float = Field(..., gt=0)

class ShippingAddressSchema(BaseModel):
    """Shipping address schema"""
    street: str
    city: str
    state: str
    country: str
    postal_code: str

class OrderBase(BaseModel):
    """Base order schema"""
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    items: List[OrderItemSchema]
    currency: str = "USD"
    shipping_address: Optional[ShippingAddressSchema] = None
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    """Create order schema"""
    organization_id: str

class OrderUpdate(BaseModel):
    """Update order schema"""
    customer_name: Optional[str] = Field(None, min_length=1, max_length=200)
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    status: Optional[str] = None
    payment_status: Optional[str] = None
    shipping_address: Optional[ShippingAddressSchema] = None
    notes: Optional[str] = None

class OrderResponse(OrderBase):
    """Order response schema"""
    id: str
    order_number: str
    workspace_id: str
    organization_id: str
    total_amount: float
    status: str
    payment_status: str
    order_date: datetime
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True