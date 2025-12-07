"""
Order Models
Database entities and DTOs for order management
"""
from pydantic import Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.base import BaseSchema, BaseDTO, TimestampMixin
from app.models.enums import OrderType, OrderStatus, PaymentStatus, PaymentMethod, OrderSource
from app.models.customer import CustomerCreateDTO


# =============================================================================
# DATABASE ENTITIES
# =============================================================================

class OrderItem(BaseSchema):
    """Order item embedded schema"""
    menu_item_id: str
    menu_item_name: str
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., gt=0)
    special_instructions: Optional[str] = Field(None, max_length=500)


class Order(BaseSchema, TimestampMixin):
    """Order collection schema"""
    id: str
    order_number: str
    venue_id: str
    customer_id: str
    order_type: OrderType
    table_id: Optional[str] = None
    items: List[OrderItem]
    subtotal: float = Field(..., ge=0)
    tax_amount: float = Field(default=0.0, ge=0)
    discount_amount: float = Field(default=0.0, ge=0)
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payment_method: Optional[PaymentMethod] = None
    estimated_ready_time: Optional[datetime] = None
    actual_ready_time: Optional[datetime] = None
    special_instructions: Optional[str] = Field(None, max_length=1000)


# =============================================================================
# DTOs
# =============================================================================

class OrderItemCreateDTO(BaseDTO):
    """DTO for creating order items"""
    menu_item_id: str
    quantity: int = Field(..., ge=1, le=50)
    customizations: Optional[Dict[str, Any]] = Field(default_factory=dict)
    special_instructions: Optional[str] = Field(None, max_length=500)


class OrderItemResponseDTO(BaseDTO):
    """Order item response DTO"""
    menu_item_id: str
    menu_item_name: str
    quantity: int
    unit_price: float
    special_instructions: Optional[str] = None


class OrderCreateDTO(BaseDTO):
    """DTO for creating orders"""
    venue_id: str
    customer_id: str
    order_type: OrderType
    table_id: Optional[str] = None
    items: List[OrderItemCreateDTO] = Field(..., min_items=1)
    special_instructions: Optional[str] = Field(None, max_length=1000)


class PublicOrderCreateDTO(BaseDTO):
    """DTO for creating orders from public interface (QR scan)"""
    venue_id: str = Field(..., description="Venue where order is placed")
    table_id: Optional[str] = Field(None, description="Table ID from QR scan")
    customer: CustomerCreateDTO
    items: List[OrderItemCreateDTO] = Field(..., min_items=1, max_items=50)
    order_type: OrderSource = OrderSource.QR_SCAN
    special_instructions: Optional[str] = Field(None, max_length=1000)


class OrderUpdateDTO(BaseDTO):
    """DTO for updating orders"""
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    estimated_ready_time: Optional[datetime] = None
    special_instructions: Optional[str] = Field(None, max_length=1000)


class OrderResponseDTO(BaseDTO):
    """Complete order response DTO"""
    id: str
    order_number: str
    venue_id: str
    customer_id: str
    order_type: OrderType
    table_id: Optional[str] = None
    table_number: Optional[str] = None  # User-friendly table number
    items: List[OrderItemResponseDTO]
    subtotal: float
    tax_amount: float
    discount_amount: float
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: Optional[PaymentMethod] = None
    estimated_ready_time: Optional[datetime] = None
    actual_ready_time: Optional[datetime] = None
    special_instructions: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OrderCreationResponseDTO(BaseDTO):
    """Response DTO after order creation"""
    success: bool
    order_id: str
    order_number: str
    estimated_preparation_time: Optional[int] = None
    payment_required: bool
    message: str
    customer_id: str


class OrderValidationResponseDTO(BaseDTO):
    """Response DTO for order validation"""
    is_valid: bool
    venue_open: bool
    items_available: List[str] = Field(default_factory=list)
    items_unavailable: List[str] = Field(default_factory=list)
    estimated_total: float = Field(default=0.0)
    estimated_preparation_time: Optional[int] = None
    message: Optional[str] = None
    errors: List[str] = Field(default_factory=list)