from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BillingDetailCreate(BaseModel):
    workspace_id: int
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    billing_email: Optional[str] = None
    billing_phone: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


class BillingDetailUpdate(BaseModel):
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    billing_email: Optional[str] = None
    billing_phone: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


class BillingDetailResponse(BaseModel):
    id: int
    workspace_id: int
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    billing_email: Optional[str] = None
    billing_phone: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BillingTransactionCreate(BaseModel):
    workspace_id: int
    plan: str
    amount: float = Field(..., ge=0)
    currency: str = Field(default="INR", max_length=10)
    billing_period_start: datetime
    billing_period_end: datetime
    payment_status: str = Field(default="pending", max_length=30)
    payment_method: Optional[str] = None
    payment_ref: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None


class BillingTransactionUpdate(BaseModel):
    payment_status: Optional[str] = Field(None, max_length=30)
    paid_amount: Optional[float] = Field(None, ge=0)
    payment_method: Optional[str] = None
    payment_ref: Optional[str] = None
    last_paid_at: Optional[datetime] = None
    notes: Optional[str] = None


class BillingTransactionResponse(BaseModel):
    id: int
    workspace_id: int
    plan: str
    amount: float
    currency: str
    billing_period_start: datetime
    billing_period_end: datetime
    payment_status: str
    payment_method: Optional[str] = None
    payment_ref: Optional[str] = None
    invoice_number: Optional[str] = None
    last_paid_at: Optional[datetime] = None
    paid_amount: float
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
