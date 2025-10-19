"""
Data Transfer Objects (DTOs) for Dino Multi-Venue Platform
Contains API request/response objects, business logic DTOs, and validation schemas
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date, time
from enum import Enum
import re

# Import enums from schemas to avoid duplication
from app.models.schemas import (
    UserRole, BusinessType, SubscriptionPlan, SubscriptionStatus, VenueStatus,
    WorkspaceStatus, OrderStatus, PaymentStatus, PaymentMethod, PaymentGateway,
    OrderType, OrderSource, TableStatus, NotificationType, TransactionType,
    FeedbackType, PriceRange, SpiceLevel, Priority,
    VenueLocation, VenueOperatingHours
)


# =============================================================================
# BASE DTOs
# =============================================================================

class BaseDTO(BaseModel):
    """Base DTO with common configuration"""
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# =============================================================================
# WORKSPACE DTOs
# =============================================================================

class WorkspaceCreateDTO(BaseDTO):
    """DTO for creating workspace"""
    name: str = Field(..., min_length=5, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class WorkspaceUpdateDTO(BaseDTO):
    """DTO for updating workspace"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

class WorkspaceResponseDTO(BaseDTO):
    """Complete workspace response DTO"""
    id: str
    name: str
    description: Optional[str] = None
    venue_ids: List[str] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# AUTH REQUEST/RESPONSE DTOs
# =============================================================================

class RefreshTokenRequest(BaseDTO):
    """Request DTO for token refresh"""
    refresh_token: str = Field(..., description="Refresh token to exchange for new access token")

class ChangePasswordRequest(BaseDTO):
    """Request DTO for password change"""
    current_password: str = Field(..., description="Current user password")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator('new_password')
    def validate_new_password_strength(cls, v):
        # Basic validation - detailed validation handled by password handler
        if len(v) < 8:
            raise ValueError('New password must be at least 8 characters long')
        return v

class GetSaltRequest(BaseDTO):
    """Request DTO for getting user salt for client-side hashing"""
    email: EmailStr = Field(..., description="User email to get salt for")

class ClientHashedLoginRequest(BaseDTO):
    """Request DTO for login with client-side hashed password"""
    email: EmailStr = Field(..., description="User email")
    password_hash: str = Field(..., description="Client-side hashed password")

# =============================================================================
# USER DTOs
# =============================================================================

class UserCreateDTO(BaseDTO):
    """DTO for creating users"""
    email: EmailStr
    phone: str = Field(..., pattern="^[0-9]{10}$", description="Unique phone number")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    role_id: str = Field(..., description="Role ID reference")
    venue_ids: List[str] = Field(default_factory=list, description="List of venue IDs user has access to")

    @validator('password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r"[A-Z]", v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r"[a-z]", v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r"\d", v):
            raise ValueError('Password must contain at least one digit')
        return v

class AdminUserCreateDTO(BaseDTO):
    """DTO for creating users by admin with pre-hashed password"""
    email: EmailStr
    phone: str = Field(..., pattern="^[0-9]{10}$", description="Unique phone number")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., description="Pre-hashed password from UI")
    role_id: str = Field(..., description="Role ID reference")
    venue_ids: List[str] = Field(default_factory=list, description="List of venue IDs user has access to")

class UserLoginDTO(BaseDTO):
    """User login DTO"""
    email: EmailStr
    password: str
    remember_me: bool = Field(default=False)

class UserUpdateDTO(BaseDTO):
    """DTO for updating users"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, pattern="^[0-9]{10}$")
    is_active: Optional[bool] = None

class UserResponseDTO(BaseDTO):
    """Complete user response DTO"""
    id: str
    email: EmailStr
    phone: str = Field(default="", description="Phone number - required but can be empty during migration")
    first_name: str
    last_name: str
    role_id: str = Field(default="unknown", description="Role ID reference - required but can be unknown during migration")
    venue_ids: List[str] = Field(default_factory=list, description="List of venue IDs user has access to")
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    email_verified: bool = Field(default=False)
    phone_verified: bool = Field(default=False)
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# VENUE DTOs
# =============================================================================

class VenueCreateDTO(BaseDTO):
    """DTO for creating venues"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    location: VenueLocation
    phone: str = Field(..., pattern="^[0-9]{10}$")
    email: Optional[EmailStr] = None
    workspace_id: str = Field(..., description="Workspace this venue belongs to")
    price_range: PriceRange
    subscription_plan: SubscriptionPlan = SubscriptionPlan.BASIC
    subscription_status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    admin_id: Optional[str] = None
    logo_url: Optional[str] = None

class VenueUpdateDTO(BaseDTO):
    """DTO for updating venues"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    phone: Optional[str] = Field(None, pattern="^[0-9]{10}$")
    email: Optional[EmailStr] = None

    logo_url: Optional[str] = None
    price_range: Optional[PriceRange] = None
    subscription_plan: Optional[SubscriptionPlan] = None
    subscription_status: Optional[SubscriptionStatus] = None
    status: Optional[VenueStatus] = None
    is_active: Optional[bool] = None

class VenueResponseDTO(BaseDTO):
    """Complete venue response DTO"""
    id: str
    name: str
    description: str
    location: VenueLocation
    phone: str
    email: Optional[EmailStr] = None
    workspace_id: str = Field(..., description="Workspace this venue belongs to")
    logo_url: Optional[str] = None
    price_range: PriceRange
    subscription_plan: SubscriptionPlan
    subscription_status: SubscriptionStatus
    status: VenueStatus
    is_active: bool
    rating_total: float = Field(description="Sum of all ratings")
    rating_count: int = Field(description="Number of ratings received")
    admin_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    logo_url: Optional[str] = None

class VenuePublicInfoDTO(BaseDTO):
    """Public venue information DTO for QR access"""
    id: str
    name: str
    description: Optional[str] = None
    location: VenueLocation
    phone: str

    price_range: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    is_open: bool
    current_wait_time: Optional[int] = None
    rating_total: float = Field(default=0.0, description="Sum of all ratings")
    rating_count: int = Field(default=0, description="Number of ratings received")
    average_rating: float = Field(default=0.0, description="Calculated average rating")
    logo_url: Optional[str] = None

class VenueWorkspaceListDTO(BaseDTO):
    """Simplified venue information DTO for workspace venue listings"""
    id: str
    name: str
    description: Optional[str] = None
    location: Dict[str, str] = Field(default_factory=dict, description="Simplified location info")
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    is_open: bool = Field(default=False, description="Current operational status")
    status: VenueStatus
    subscription_status: SubscriptionStatus
    created_at: datetime
    updated_at: datetime


# =============================================================================
# MENU DTOs
# =============================================================================

class MenuCategoryCreateDTO(BaseDTO):
    """DTO for creating menu categories"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    venue_id: str

class MenuCategoryUpdateDTO(BaseDTO):
    """DTO for updating menu categories"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None

class MenuCategoryResponseDTO(BaseDTO):
    """Complete menu category response DTO"""
    id: str
    venue_id: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

class MenuItemCreateDTO(BaseDTO):
    """DTO for creating menu items"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    base_price: float = Field(..., gt=0)
    category_id: str
    venue_id: str
    is_vegetarian: bool = Field(default=True)
    spice_level: SpiceLevel = SpiceLevel.MILD
    preparation_time_minutes: int = Field(..., ge=5, le=120)

class MenuItemUpdateDTO(BaseDTO):
    """DTO for updating menu items"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    base_price: Optional[float] = Field(None, gt=0)
    category_id: Optional[str] = None
    is_vegetarian: Optional[bool] = None
    spice_level: Optional[SpiceLevel] = None
    preparation_time_minutes: Optional[int] = Field(None, ge=5, le=120)
    is_available: Optional[bool] = None

class MenuItemResponseDTO(BaseDTO):
    """Complete menu item response DTO"""
    id: str
    venue_id: str
    category_id: str
    name: str
    description: str
    base_price: float
    is_vegetarian: bool
    spice_level: SpiceLevel
    preparation_time_minutes: int
    image_urls: List[str] = Field(default_factory=list)
    is_available: bool
    rating_total: float = Field(description="Sum of all ratings")
    rating_count: int = Field(description="Number of ratings received")
    average_rating: float = Field(description="Calculated average rating")
    created_at: datetime
    updated_at: datetime


# =============================================================================
# TABLE DTOs
# =============================================================================

class TableAreaCreateDTO(BaseDTO):
    """DTO for creating table areas"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, max_length=7, description="Hex color code")
    venue_id: str
    active: Optional[bool] = Field(default=True, alias="active")

    class Config:
        populate_by_name = True

class TableAreaUpdateDTO(BaseDTO):
    """DTO for updating table areas"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, max_length=7, description="Hex color code")
    active: Optional[bool] = None
    is_active: Optional[bool] = None

class TableAreaResponseDTO(BaseDTO):
    """Complete table area response DTO"""
    id: str
    venue_id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: bool
    active: bool
    created_at: datetime
    updated_at: datetime

class TableCreateDTO(BaseDTO):
    """DTO for creating tables"""
    table_number: str = Field(..., description="Table number as string")
    capacity: int = Field(..., ge=1, le=20)
    location: Optional[str] = Field(None, max_length=100)
    area_id: Optional[str] = Field(None, description="Table area ID")
    venue_id: str

class TableUpdateDTO(BaseDTO):
    """DTO for updating tables"""
    capacity: Optional[int] = Field(None, ge=1, le=20)
    location: Optional[str] = Field(None, max_length=100)
    area_id: Optional[str] = None
    table_status: Optional[TableStatus] = None
    is_active: Optional[bool] = None

class TableResponseDTO(BaseDTO):
    """Complete table response DTO"""
    id: str
    venue_id: str
    table_number: str
    capacity: int
    location: Optional[str] = None
    area_id: Optional[str] = None
    table_status: TableStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# CUSTOMER DTOs
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
    total_orders: int
    total_spent: float
    last_order_date: Optional[datetime] = None
    favorite_venue_id: Optional[str] = None
    loyalty_points: int
    marketing_consent: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# ORDER DTOs
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
    total_price: float
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
    items: List[OrderItemResponseDTO]
    subtotal: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: Optional[PaymentMethod] = None
    estimated_ready_time: Optional[datetime] = None
    actual_ready_time: Optional[datetime] = None
    special_instructions: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# ROLE DTOs
# =============================================================================

class RoleCreateDTO(BaseDTO):
    """DTO for creating roles"""
    name: str = Field(..., description="Role name (e.g., 'superadmin', 'admin', 'operator')")
    description: str = Field(..., min_length=5, max_length=500, description="Role description")
    permission_ids: List[str] = Field(default_factory=list, description="List of permission IDs")
    
    @validator('name')
    def validate_name(cls, v):
        # Validate role name format
        if not v or len(v.strip()) == 0:
            raise ValueError('Role name cannot be empty')
        # Convert to lowercase for consistency
        return v.lower().strip()

class RoleUpdateDTO(BaseDTO):
    """DTO for updating roles"""
    description: Optional[str] = Field(None, min_length=5, max_length=500)
    permission_ids: Optional[List[str]] = None

class RoleResponseDTO(BaseDTO):
    """Complete role response DTO"""
    id: str
    name: str = Field(..., description="Role name")
    description: str
    permission_ids: List[str] = Field(default_factory=list)
    permissions: List[Dict[str, Any]] = Field(default_factory=list)
    user_count: int = Field(default=0, description="Number of users with this role")
    created_at: datetime
    updated_at: datetime

class RoleFiltersDTO(BaseDTO):
    """Role filtering options DTO"""
    search: Optional[str] = None

class RolePermissionMappingDTO(BaseDTO):
    """Role-permission mapping DTO"""
    role_id: str
    permission_ids: List[str]

class RoleAssignmentDTO(BaseDTO):
    """Role assignment to user DTO"""
    user_id: str
    role_id: str
    workspace_id: Optional[str] = None
    venue_id: Optional[str] = None

class RoleStatisticsDTO(BaseDTO):
    """Role statistics DTO"""
    total_roles: int = 0
    users_by_role: Dict[str, int] = Field(default_factory=dict)

class BulkPermissionAssignmentDTO(BaseDTO):
    """DTO for bulk permission assignment"""
    permission_ids: List[str] = Field(..., description="List of permission IDs to assign")


# =============================================================================
# PERMISSION DTOs
# =============================================================================

class PermissionCreateDTO(BaseDTO):
    """DTO for creating permissions"""
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

class PermissionUpdateDTO(BaseDTO):
    """DTO for updating permissions"""
    description: Optional[str] = Field(None, max_length=500)

class PermissionResponseDTO(BaseDTO):
    """Complete permission response DTO"""
    id: str
    name: str
    description: str
    resource: str
    action: str
    scope: str
    roles_count: int = Field(default=0, description="Number of roles with this permission")
    created_at: datetime

class PermissionFiltersDTO(BaseDTO):
    """Permission filtering options DTO"""
    name: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    scope: Optional[str] = None
    search: Optional[str] = None

class PermissionCategoryDTO(BaseDTO):
    """Permission category DTO"""
    name: str
    display_name: str
    description: str
    permissions: List[PermissionResponseDTO] = Field(default_factory=list)

class PermissionMatrixDTO(BaseDTO):
    """Permission matrix DTO"""
    resources: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    matrix: Dict[str, Dict[str, Optional[PermissionResponseDTO]]] = Field(default_factory=dict)

class PermissionStatisticsDTO(BaseDTO):
    """Permission statistics DTO"""
    total_permissions: int = 0
    permissions_by_resource: Dict[str, int] = Field(default_factory=dict)
    permissions_by_action: Dict[str, int] = Field(default_factory=dict)
    permissions_by_category: Dict[str, int] = Field(default_factory=dict)
    unused_permissions: int = 0

class BulkPermissionCreateDTO(BaseDTO):
    """DTO for bulk permission creation"""
    permissions: List[PermissionCreateDTO] = Field(..., min_items=1, max_items=100)

class BulkPermissionResponseDTO(BaseDTO):
    """Response DTO for bulk operations"""
    success: bool = True
    created: int = 0
    skipped: int = 0
    errors: List[str] = Field(default_factory=list)
    created_permissions: List[PermissionResponseDTO] = Field(default_factory=list)

class PermissionCheckDTO(BaseDTO):
    """Permission check result DTO"""
    has_permission: bool
    reason: Optional[str] = None


# =============================================================================
# WORKSPACE ONBOARDING DTOs
# =============================================================================

class UserDetailsDTO(BaseDTO):
    """Owner/SuperAdmin details DTO for workspace creation"""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    date_of_birth: Optional[datetime] = None
    address: Optional[str] = Field(None, max_length=500)

class WorkspaceRegistrationDTO(BaseDTO):
    """Workspace registration DTO"""
    # Workspace details
    workspace_name: str = Field(..., min_length=5, max_length=100, alias="workspaceName")
    workspace_description: Optional[str] = Field(None, max_length=500, alias="workspaceDescription")
    
    # Venue details
    venue_name: str = Field(..., min_length=1, max_length=100, alias="venueName")
    venue_description: Optional[str] = Field(None, max_length=1000, alias="venueDescription")
    venue_type: Optional[str] = Field(None, alias="venueType")
    venue_location: VenueLocation = Field(..., alias="venueLocation")
    venue_phone: Optional[str] = Field(None, pattern="^[0-9]{10}$", alias="venuePhone")
    venue_email: Optional[EmailStr] = Field(None, alias="venueEmail")
    price_range: PriceRange = Field(..., alias="priceRange")
    
    # Owner details
    owner_first_name: str = Field(..., min_length=1, max_length=50, alias="ownerFirstName")
    owner_last_name: str = Field(..., min_length=1, max_length=50, alias="ownerLastName")
    owner_email: EmailStr = Field(..., alias="ownerEmail")
    owner_phone: Optional[str] = Field(None, pattern="^[0-9]{10}$", alias="ownerPhone")
    owner_password: str = Field(..., min_length=8, max_length=128, alias="ownerPassword")
    
    class Config:
        populate_by_name = True

    @validator('owner_password')
    def validate_password_strength(cls, v):
        # Password validation is now handled by unified password handler
        # This validator is kept for basic length check only
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    def get_owner_phone_number(self) -> Optional[str]:
        """Get owner phone number from any available field"""
        return self.owner_phone
    
    def get_venue_phone_number(self) -> Optional[str]:
        """Get venue phone number from any available field"""
        return self.venue_phone or self.get_owner_phone_number()


# =============================================================================
# QR CODE AND PUBLIC ACCESS DTOs
# =============================================================================

class QRCodeDataDTO(BaseDTO):
    """QR code data structure DTO"""
    venue_id: str
    table_id: str
    table_number: int
    encrypted_token: str
    generated_at: datetime

class MenuPublicAccessDTO(BaseDTO):
    """Public menu access response DTO"""
    venue: VenuePublicInfoDTO
    table: Optional[Dict[str, Any]] = None
    categories: List[Dict[str, Any]] = Field(default_factory=list)
    items: List[Dict[str, Any]] = Field(default_factory=list)
    special_offers: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_preparation_times: Dict[str, int] = Field(default_factory=dict)

class VenueOperatingStatusDTO(BaseDTO):
    """Current venue operating status DTO"""
    venue_id: str
    is_open: bool
    current_status: VenueStatus
    next_opening: Optional[datetime] = None
    next_closing: Optional[datetime] = None
    break_time: Optional[Dict[str, datetime]] = None
    message: str

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


# =============================================================================
# ANALYTICS DTOs
# =============================================================================

class SalesAnalyticsDTO(BaseDTO):
    """Consolidated sales analytics DTO"""
    total_revenue: float
    total_orders: int
    average_order_value: float
    popular_items: List[Dict[str, Any]] = Field(default_factory=list)
    revenue_by_day: List[Dict[str, Any]] = Field(default_factory=list)
    orders_by_status: List[Dict[str, Any]] = Field(default_factory=list)

class VenueAnalyticsDTO(BaseDTO):
    """Venue analytics data DTO"""
    venue_id: str
    venue_name: str
    period: str
    total_orders: int = 0
    total_revenue: float = 0.0
    average_order_value: float = 0.0
    total_customers: int = 0
    new_customers: int = 0
    returning_customers: int = 0
    popular_items: List[Dict[str, Any]] = Field(default_factory=list)
    peak_hours: List[Dict[str, Any]] = Field(default_factory=list)
    table_utilization: float = 0.0
    customer_satisfaction: float = 0.0
    order_status_breakdown: Dict[str, int] = Field(default_factory=dict)

class DashboardStatsDTO(BaseDTO):
    """Dashboard statistics DTO"""
    total_orders_today: int = Field(default=0)
    total_revenue_today: float = Field(default=0.0)
    pending_orders: int = Field(default=0)
    active_customers: int = Field(default=0)
    average_order_value: float = Field(default=0.0)
    popular_items: List[Dict[str, Any]] = Field(default_factory=list)
    recent_orders: List[Dict[str, Any]] = Field(default_factory=list)

class DashboardDataDTO(BaseDTO):
    """Dashboard data DTO based on user role"""
    user_role: UserRole
    workspace_id: str
    venue_id: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)
    recent_orders: List[Dict[str, Any]] = Field(default_factory=list)
    analytics: Dict[str, Any] = Field(default_factory=dict)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    quick_actions: List[Dict[str, Any]] = Field(default_factory=list)

class SuperAdminDashboardDTO(DashboardDataDTO):
    """SuperAdmin dashboard DTO with workspace-wide data"""
    all_venues: List[Dict[str, Any]] = Field(default_factory=list)
    workspace_analytics: Dict[str, Any] = Field(default_factory=dict)
    user_management: Dict[str, Any] = Field(default_factory=dict)

class AdminDashboardDTO(DashboardDataDTO):
    """Admin dashboard DTO with venue-specific data"""
    venue_analytics: Optional[VenueAnalyticsDTO] = None
    staff_performance: Dict[str, Any] = Field(default_factory=dict)
    inventory_alerts: List[Dict[str, Any]] = Field(default_factory=list)

class OperatorDashboardDTO(DashboardDataDTO):
    """Operator dashboard DTO with operational data"""
    active_orders: List[Dict[str, Any]] = Field(default_factory=list)
    table_status: List[Dict[str, Any]] = Field(default_factory=list)
    today_summary: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# RESPONSE DTOs
# =============================================================================

class AuthTokenDTO(BaseDTO):
    """Authentication token response DTO"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: UserResponseDTO

class TokenDTO(BaseDTO):
    """Simple token response DTO"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponseDTO

class ApiResponseDTO(BaseDTO):
    """Standard API response DTO"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SimpleApiResponseDTO(BaseDTO):
    """Simple API response DTO without data field"""
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PaginatedResponseDTO(BaseDTO):
    """Paginated response DTO"""
    success: bool = True
    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

class ErrorResponseDTO(BaseDTO):
    """Error response DTO"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class WorkspaceRegistrationResponseDTO(BaseDTO):
    """Response DTO after successful workspace registration"""
    success: bool
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    
    class WorkspaceInfo(BaseDTO):
        id: str
        name: str
    
    class VenueInfo(BaseDTO):
        id: str
        name: str
    
    class OwnerInfo(BaseDTO):
        id: str
        first_name: str
        last_name: str
        role_id: str
        role_name: str

class WorkspaceOnboardingResponseDTO(BaseDTO):
    """Response DTO after successful workspace onboarding"""
    success: bool
    workspace_id: str
    default_venue_id: str
    superadmin_user_id: str
    access_token: str
    refresh_token: str
    message: str
    next_steps: List[str] = Field(default_factory=list)

class OrderCreationResponseDTO(BaseDTO):
    """Response DTO after order creation"""
    success: bool
    order_id: str
    order_number: str
    estimated_preparation_time: Optional[int] = None
    total_amount: float
    payment_required: bool
    message: str
    customer_id: str


# =============================================================================
# FILE UPLOAD DTOs
# =============================================================================

class ImageUploadResponseDTO(BaseDTO):
    """Image upload response DTO"""
    success: bool = True
    file_url: str
    file_name: str
    file_size: int
    content_type: str
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)

class BulkImageUploadResponseDTO(BaseDTO):
    """Bulk image upload response DTO"""
    success: bool = True
    uploaded_files: List[ImageUploadResponseDTO]
    failed_files: List[Dict[str, str]] = Field(default_factory=list)
    total_uploaded: int
    total_failed: int


# =============================================================================
# UTILITY DTOs
# =============================================================================

class RepositoryFiltersDTO(BaseDTO):
    """Generic repository filtering DTO"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")
    search: Optional[str] = Field(None, description="Search term")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Additional filters")

class NameAvailabilityDTO(BaseDTO):
    """DTO for checking name availability"""
    available: bool
    message: Optional[str] = None

class ValidationResultDTO(BaseDTO):
    """Generic validation result DTO"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# =============================================================================
# SETUP DTOs (for system initialization)
# =============================================================================

class SetupRoleDTO(BaseDTO):
    """DTO for role setup during system initialization"""
    name: UserRole
    description: str
    permission_names: List[str] = Field(default_factory=list, description="Permission names to assign")

class SetupPermissionDTO(BaseDTO):
    """DTO for permission setup during system initialization"""
    name: str
    description: str
    resource: str
    action: str
    scope: str

class SystemSetupDTO(BaseDTO):
    """DTO for complete system setup"""
    permissions: List[SetupPermissionDTO] = Field(default_factory=list)
    roles: List[SetupRoleDTO] = Field(default_factory=list)

class SetupResponseDTO(BaseDTO):
    """DTO for setup operation responses"""
    success: bool
    message: str
    created_permissions: int = 0
    created_roles: int = 0
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# LEGACY COMPATIBILITY (for existing imports)
# =============================================================================

# Keep these for backward compatibility with existing code
ApiResponse = ApiResponseDTO
PaginatedResponse = PaginatedResponseDTO
ErrorResponse = ErrorResponseDTO