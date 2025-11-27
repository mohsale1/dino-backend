"""
Customer Models
Database entities and DTOs for customer management
"""
from pydantic import Field
from typing import Optional, List
from datetime import datetime

from app.models.base import BaseSchema, BaseDTO, TimestampMixin


# =============================================================================
# DATABASE ENTITY
# =============================================================================

class Customer(BaseSchema, TimestampMixin):
    """Customer collection schema"""
    id: str
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern="^[0-9]{10}$")
    venue_ids: List[str] = Field(default_factory=list, description="List of unique venue IDs where customer has ordered")
    total_orders: int = Field(default=0)
    total_spent: float = Field(default=0.0)
    last_order_date: Optional[datetime] = None
    favorite_venue_id: Optional[str] = None
    marketing_consent: bool = Field(default=False)


# =============================================================================
# DTOs
# =============================================================================

class CustomerCreateDTO(BaseDTO):
    """DTO for creating customers"""
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern="^[0-9]{10}$")


class CustomerUpdateDTO(BaseDTO):
    """DTO for updating customers"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, pattern="^[0-9]{10}$")


class CustomerResponseDTO(BaseDTO):
    """Complete customer response DTO"""
    id: str
    name: str
    phone: str
    venue_ids: List[str] = Field(default_factory=list, description="List of unique venue IDs where customer has ordered")
    total_orders: int
    total_spent: float
    last_order_date: Optional[datetime] = None
    favorite_venue_id: Optional[str] = None
    loyalty_points: int
    marketing_consent: bool
    created_at: datetime
    updated_at: datetime