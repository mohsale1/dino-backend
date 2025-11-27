"""
Enums for Dino Multi-Venue Platform
Shared enumerations used across database entities and DTOs
"""
from enum import Enum


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