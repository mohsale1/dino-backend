from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class OrderItemSchema(BaseModel):
    """Order item schema"""
    item_id: int
    item_name: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    total_price: float = Field(..., gt=0)


class OrderBase(BaseModel):
    """Base order schema"""
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    items: List[OrderItemSchema]
    currency: str = "USD"
    special_instructions: Optional[str] = None


class OrderCreate(OrderBase):
    """Create order schema"""
    persona_id: int
    workspace_id: Optional[int] = None
    table_id: Optional[int] = None
    area_id: Optional[int] = None
    order_type: str = "dine_in"
    subtotal: float = 0
    tax_amount: float = 0
    service_charge: float = 0
    discount_amount: float = 0
    payment_method: Optional[str] = None


class OrderUpdate(BaseModel):
    """Update order schema"""
    customer_name: Optional[str] = Field(None, min_length=1, max_length=200)
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    status: Optional[str] = None
    payment_status: Optional[str] = None
    special_instructions: Optional[str] = None


class OrderResponse(OrderBase):
    """Order response schema"""
    id: int
    order_number: str
    workspace_id: int
    persona_id: int
    total_amount: float
    status: str
    payment_status: str
    order_date: datetime
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
