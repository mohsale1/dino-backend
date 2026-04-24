from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class OrderLineItem(BaseModel):
    """A single line item in an order creation request."""
    item_id: int
    item_name: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)


class OrderDetailCreate(BaseModel):
    """Create an order with line items."""
    order_type: Literal['dine_in', 'takeaway', 'delivery'] = 'dine_in'
    customer_id: Optional[int] = None
    customer_name: str = Field(..., min_length=1, max_length=200)
    table_id: Optional[int] = None
    area_id: Optional[int] = None
    currency: str = Field(default="INR", max_length=10)
    special_instructions: Optional[str] = Field(None, max_length=1000)
    items: List[OrderLineItem]


class OrderDetailUpdate(BaseModel):
    status: Optional[Literal['pending', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled']] = None
    customer_name: Optional[str] = Field(None, min_length=1, max_length=200)
    table_id: Optional[int] = None
    area_id: Optional[int] = None
    special_instructions: Optional[str] = Field(None, max_length=1000)


class OrderDetailResponse(BaseModel):
    id: int
    order_id: str
    order_type: str
    status: str
    customer_id: Optional[int] = None
    customer_name: str
    table_id: Optional[int] = None
    area_id: Optional[int] = None
    subtotal: float
    tax_amount: float
    service_charge: float
    discount_amount: float
    total_amount: float
    currency: str
    special_instructions: Optional[str] = None
    workspace_id: int
    persona_id: int
    created_by: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    """Response for a single order line item."""
    sino: int
    order_id: str
    item_id: int
    item_name: str
    quantity: int
    unit_price: float
    line_total: float
    workspace_id: int
    persona_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderTransactionCreate(BaseModel):
    order_id: str
    customer_id: Optional[int] = None
    paid_amount: float = Field(default=0, ge=0)
    total_amount: float = Field(default=0, ge=0)
    currency: str = Field(default="INR", max_length=10)
    payment_method: Optional[str] = None
    payment_status: Literal['unpaid', 'partial', 'paid', 'refunded'] = 'unpaid'
    payment_ref: Optional[str] = None
    notes: Optional[str] = None


class OrderTransactionUpdate(BaseModel):
    payment_status: Optional[Literal['unpaid', 'partial', 'paid', 'refunded']] = None
    paid_amount: Optional[float] = Field(None, ge=0)
    payment_method: Optional[str] = None
    payment_ref: Optional[str] = None
    notes: Optional[str] = None


class OrderTransactionResponse(BaseModel):
    id: int
    order_id: str
    customer_id: Optional[int] = None
    workspace_id: int
    persona_id: int
    paid_amount: float
    total_amount: float
    currency: str
    payment_method: Optional[str] = None
    payment_status: str
    payment_ref: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
