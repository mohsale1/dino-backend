"""
Database Collection Schemas for Dino Multi-Venue Platform
Contains ONLY database entity schemas - no API DTOs or business logic objects
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, time
from enum import Enum
import re


# =============================================================================
# ENUMS (Shared across database and DTOs)
# =============================================================================

class UserRole(str, Enum):
    """User roles with hierarchy"""
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    OPERATOR = "operator"

class BusinessType(str, Enum):
    """Business types"""
    VENUE = "venue"
    RESTAURANT = "restaurant"
    BOTH = "both"

class SubscriptionPlan(str, Enum):
    """Subscription plans"""
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(str, Enum):
    """Subscription status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class VenueStatus(str, Enum):
    """Venue operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    CLOSED = "closed"

class WorkspaceStatus(str, Enum):
    """Workspace status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"

class OrderStatus(str, Enum):
    """Order status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    SERVED = "served"
    DELIVERED = "delivered"
    OUT_FOR_DELIVERY = "out_for_delivery"
    CANCELLED = "cancelled"

class PaymentStatus(str, Enum):
    """Payment status"""
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"

class PaymentMethod(str, Enum):
    """Payment methods"""
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    WALLET = "wallet"
    NET_BANKING = "net_banking"

class PaymentGateway(str, Enum):
    """Payment gateways"""
    RAZORPAY = "razorpay"
    STRIPE = "stripe"
    PAYPAL = "paypal"
    PAYTM = "paytm"
    CASH = "cash"

class OrderType(str, Enum):
    """Order types"""
    DINE_IN = "dine_in"
    TAKEAWAY = "takeaway"

class OrderSource(str, Enum):
    """Order source types"""
    QR_SCAN = "qr_scan"
    WALK_IN = "walk_in"
    ONLINE = "online"
    PHONE = "phone"

class TableStatus(str, Enum):
    """Table status"""
    AVAILABLE = "available"
    RESERVED = "reserved"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"

class NotificationType(str, Enum):
    """Notification types"""
    ORDER_PLACED = "order_placed"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_READY = "order_ready"
    ORDER_DELIVERED = "order_delivered"
    PAYMENT_RECEIVED = "payment_received"
    SYSTEM_ALERT = "system_alert"

class TransactionType(str, Enum):
    """Transaction types"""
    PAYMENT = "payment"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"

class FeedbackType(str, Enum):
    """Feedback types"""
    ORDER = "order"
    SERVICE = "service"
    FOOD = "food"
    AMBIANCE = "ambiance"
    OVERALL = "overall"

class PriceRange(str, Enum):
    """Price ranges"""
    BUDGET = "budget"
    MID_RANGE = "mid_range"
    PREMIUM = "premium"
    LUXURY = "luxury"

class SpiceLevel(str, Enum):
    """Spice levels"""
    MILD = "mild"
    MEDIUM = "medium"
    HOT = "hot"
    EXTRA_HOT = "extra_hot"

class Priority(str, Enum):
    """Priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# =============================================================================
# BASE MODELS
# =============================================================================

class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# =============================================================================
# EMBEDDED SCHEMAS (Used within collections)
# =============================================================================

class VenueLocation(BaseModel):
    """Venue location details"""
    address: str = Field(..., min_length=5, max_length=500)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=3, max_length=20)
    landmark: Optional[str] = Field(None, max_length=200)

class VenueOperatingHours(BaseModel):
    """Operating hours for a venue"""
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    is_open: bool = Field(default=True, description="Whether venue is open on this day")
    open_time: Optional[time] = Field(None, description="Opening time")
    close_time: Optional[time] = Field(None, description="Closing time")


# =============================================================================
# DATABASE COLLECTION SCHEMAS
# =============================================================================

class Workspace(BaseSchema, TimestampMixin):
    """Workspace collection schema"""
    id: str
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)

class User(BaseSchema, TimestampMixin):
    """User collection schema"""
    id: str
    email: EmailStr
    phone: str = Field(..., description="Unique phone number - required")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    hashed_password: str = Field(..., description="Hashed password")
    role_id: str = Field(..., description="Role ID reference")
    venue_ids: List[str] = Field(default_factory=list, description="List of venue IDs user has access to")
    venu_ids: Optional[List[str]] = Field(default_factory=list, description="Legacy field - use venue_ids instead")
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    email_verified: bool = Field(default=False)
    phone_verified: bool = Field(default=False)
    last_login: Optional[datetime] = None
    first_login_completed: bool = Field(default=False, description="Whether user has completed their first login flow")
    tour_completed: bool = Field(default=False, description="Whether user has completed the dashboard tour")
    tour_completed_at: Optional[datetime] = Field(None, description="When the user completed the tour")
    tour_skipped: bool = Field(default=False, description="Whether user skipped the tour")
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format - required field"""
        if not v or v == "":
            raise ValueError('Phone number is required')
        if not re.match(r"^[0-9]{10}$", v):
            raise ValueError('Invalid phone number format')
        return v
    
    @classmethod
    def from_dict(cls, user_data: Dict[str, Any]) -> 'User':
        """Create User instance from dict, handling field mapping from database"""
        data = user_data.copy()
        
        # Ensure phone field is properly set - now required
        if not data.get("phone"):
            raise ValueError("Phone number is required for user creation")
            
        # Ensure venue_ids is a list
        if 'venue_ids' not in data:
            data['venue_ids'] = []
            
        return cls(**data)

class Venue(BaseSchema, TimestampMixin):
    """Venue collection schema"""
    id: str
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    location: VenueLocation
    phone: str = Field(..., pattern="^[0-9]{10}$")
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    workspace_id: str = Field(..., description="Workspace this venue belongs to")
    price_range: PriceRange
    subscription_plan: SubscriptionPlan = SubscriptionPlan.BASIC
    subscription_status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    status: VenueStatus = VenueStatus.ACTIVE
    is_active: bool = Field(default=True)
    is_open: bool = Field(default=True, description="Whether venue is currently open for orders")
    rating_total: float = Field(default=0.0, ge=0, description="Sum of all ratings")
    rating_count: int = Field(default=0, ge=0, description="Number of ratings received")
    admin_id: Optional[str] = None
    
    @validator('website')
    def validate_venue_website(cls, v):
        """Validate website URL - allow empty strings"""
        if v is None or v == "":
            return None
        if not v.startswith(('http://', 'https://')):
            v = f"https://{v}"
        return v
    
    @property
    def average_rating(self) -> float:
        """Calculate average rating from rating_total and rating_count"""
        if self.rating_count == 0:
            return 0.0
        return round(self.rating_total / self.rating_count, 2)

class MenuCategory(BaseSchema, TimestampMixin):
    """Menu category collection schema"""
    id: str
    venue_id: str
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    image_url: Optional[str] = None
    is_active: bool = Field(default=True)

class MenuItem(BaseSchema, TimestampMixin):
    """Menu item collection schema"""
    id: str
    venue_id: str
    category_id: str
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    base_price: float = Field(..., gt=0)
    is_vegetarian: bool = Field(default=True)
    spice_level: SpiceLevel = SpiceLevel.MILD
    preparation_time_minutes: int = Field(..., ge=5, le=120)
    image_urls: List[str] = Field(default_factory=list)
    is_available: bool = Field(default=True)
    rating_total: float = Field(default=0.0, ge=0, description="Sum of all ratings")
    rating_count: int = Field(default=0, ge=0, description="Number of ratings received")
    
    @property
    def average_rating(self) -> float:
        """Calculate average rating from rating_total and rating_count"""
        if self.rating_count == 0:
            return 0.0
        return round(self.rating_total / self.rating_count, 2)

class TableArea(BaseSchema, TimestampMixin):
    """Table area collection schema"""
    id: str
    venue_id: str
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, max_length=7, description="Hex color code")
    is_active: bool = Field(default=True)
    active: bool = Field(default=True)  # For API compatibility
    
    @validator('color')
    def validate_color(cls, v):
        """Validate hex color code"""
        if v is None:
            return v
        if not v.startswith('#'):
            v = f"#{v}"
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be a valid hex color code')
        return v

class Table(BaseSchema, TimestampMixin):
    """Table collection schema"""
    id: str
    venue_id: str
    table_number: str = Field(..., description="Table number as string")
    capacity: int = Field(..., ge=1, le=20)
    location: Optional[str] = Field(None, max_length=100)
    area_id: Optional[str] = Field(None, description="Table area ID")
    table_status: TableStatus = TableStatus.AVAILABLE
    is_active: bool = Field(default=True)

class Customer(BaseSchema, TimestampMixin):
    """Customer collection schema"""
    id: str
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern="^[0-9]{10}$")
    total_orders: int = Field(default=0)
    total_spent: float = Field(default=0.0)
    last_order_date: Optional[datetime] = None
    favorite_venue_id: Optional[str] = None
    marketing_consent: bool = Field(default=False)

class OrderItem(BaseSchema):
    """Order item embedded schema"""
    menu_item_id: str
    menu_item_name: str
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., gt=0)
    total_price: float = Field(..., gt=0)
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
    total_amount: float = Field(..., gt=0)
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payment_method: Optional[PaymentMethod] = None
    estimated_ready_time: Optional[datetime] = None
    actual_ready_time: Optional[datetime] = None
    special_instructions: Optional[str] = Field(None, max_length=1000)

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

class Notification(BaseSchema, TimestampMixin):
    """Notification collection schema"""
    id: str
    recipient_id: str
    recipient_type: str
    notification_type: NotificationType
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    data: Optional[Dict[str, Any]] = None
    priority: Priority = Priority.NORMAL
    is_read: bool = Field(default=False)
    read_at: Optional[datetime] = None

class Review(BaseSchema, TimestampMixin):
    """Review collection schema"""
    id: str
    venue_id: str
    order_id: str
    customer_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)
    feedback_type: FeedbackType = FeedbackType.OVERALL
    is_verified: bool = Field(default=False)
    helpful_count: int = Field(default=0)

class Role(BaseSchema, TimestampMixin):
    """Role collection schema"""
    id: str
    name: str = Field(..., description="Role name (e.g., 'superadmin', 'admin', 'operator')")
    description: str = Field(..., max_length=500)
    permission_ids: List[str] = Field(default_factory=list)

class Permission(BaseSchema, TimestampMixin):
    """Permission collection schema"""
    id: str
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)
    scope: str = Field(..., min_length=1, max_length=50)
    
    @validator('name')
    def validate_name_format(cls, v):
        """Validate permission name format - must use dot separator"""
        if '.' not in v:
            raise ValueError('Name must follow resource.action format (e.g., venue.read)')
        
        parts = v.split('.')
        if len(parts) < 2:
            raise ValueError('Name must follow resource.action format (e.g., venue.read)')
        
        return v