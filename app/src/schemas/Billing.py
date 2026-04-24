from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BillingDetailCreate(BaseModel):
    legal_name: Optional[str] = Field(None, max_length=200)
    trade_name: Optional[str] = Field(None, max_length=200)
    gstin: Optional[str] = Field(None, max_length=15, pattern=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
    pan: Optional[str] = Field(None, max_length=10, pattern=r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
    billing_email: Optional[EmailStr] = None
    billing_phone: Optional[str] = Field(None, max_length=30, pattern=r'^\+?[0-9\s\-\(\)]{7,30}$')
    address_line1: Optional[str] = Field(None, max_length=300)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)


class BillingDetailUpdate(BaseModel):
    legal_name: Optional[str] = Field(None, max_length=200)
    trade_name: Optional[str] = Field(None, max_length=200)
    gstin: Optional[str] = Field(None, max_length=15, pattern=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
    pan: Optional[str] = Field(None, max_length=10, pattern=r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
    billing_email: Optional[EmailStr] = None
    billing_phone: Optional[str] = Field(None, max_length=30, pattern=r'^\+?[0-9\s\-\(\)]{7,30}$')
    address_line1: Optional[str] = Field(None, max_length=300)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)


class BillingDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class BillingTransactionCreate(BaseModel):
    workspace_id: int
    plan: str
    amount: float = Field(..., ge=0)
    currency: str = Field(default="INR", max_length=10)
    billing_period_start: datetime
    billing_period_end: datetime
    payment_status: Literal['pending', 'paid', 'failed', 'refunded'] = 'pending'
    payment_method: Optional[str] = None
    payment_ref: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None


class BillingTransactionUpdate(BaseModel):
    payment_status: Optional[Literal['pending', 'paid', 'failed', 'refunded']] = None
    paid_amount: Optional[float] = Field(None, ge=0)
    payment_method: Optional[str] = None
    payment_ref: Optional[str] = None
    last_paid_at: Optional[datetime] = None
    notes: Optional[str] = None


class BillingTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
