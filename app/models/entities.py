"""
Entity Models - Compatibility Layer
Re-exports all database entities for backward compatibility with imports
"""

# Re-export all enums
from app.models.enums import (
    UserRole, BusinessType, SubscriptionPlan, SubscriptionStatus,
    VenueStatus, WorkspaceStatus, OrderStatus, PaymentStatus,
    PaymentMethod, PaymentGateway, OrderType, OrderSource,
    TableStatus, NotificationType, TransactionType, FeedbackType,
    PriceRange, SpiceLevel, Priority
)

# Re-export all database entities
from app.models.workspace import Workspace
from app.models.user import User
from app.models.venue import Venue
from app.models.menu import MenuCategory, MenuItem
from app.models.table import Table, TableArea
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.role import Role
from app.models.permission import Permission
from app.models.transaction import Transaction
from app.models.notification import Notification
from app.models.review import Review

# Re-export base models
from app.models.base import VenueLocation, VenueOperatingHours

__all__ = [
    # Enums
    'UserRole', 'BusinessType', 'SubscriptionPlan', 'SubscriptionStatus',
    'VenueStatus', 'WorkspaceStatus', 'OrderStatus', 'PaymentStatus',
    'PaymentMethod', 'PaymentGateway', 'OrderType', 'OrderSource',
    'TableStatus', 'NotificationType', 'TransactionType', 'FeedbackType',
    'PriceRange', 'SpiceLevel', 'Priority',
    
    # Database Entities
    'Workspace', 'User', 'Venue', 'MenuCategory', 'MenuItem',
    'Table', 'TableArea', 'Customer', 'Order', 'OrderItem',
    'Role', 'Permission', 'Transaction', 'Notification', 'Review',
    
    # Base Models
    'VenueLocation', 'VenueOperatingHours',
]