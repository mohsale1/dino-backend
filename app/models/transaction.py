"""
Transaction Models
Database entities and DTOs for transaction management
"""
from pydantic import Field
from typing import Optional, Dict, Any
from datetime import datetime

from app.models.base import BaseSchema, TimestampMixin
from app.models.enums import TransactionType, PaymentMethod, PaymentGateway, PaymentStatus


# =============================================================================
# DATABASE ENTITY
# =============================================================================

class Transaction(BaseSchema, TimestampMixin):
    """Transaction collection schema"""
    id: str
    venue_id: str
    order_id: str
    amount: float = Field(..., gt=0)
    transaction_type: TransactionType
    payment_method: PaymentMethod
    payment_gateway: Optional[PaymentGateway] = None
    gateway_transaction_id: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None
    status: PaymentStatus
    processed_at: Optional[datetime] = None
    refunded_amount: float = Field(default=0.0, ge=0)