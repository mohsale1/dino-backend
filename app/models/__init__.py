"""
Models Package
Centralized exports for all database entities and DTOs
"""

# =============================================================================
# ENUMS
# =============================================================================
from app.models.enums import (
    UserRole, BusinessType, SubscriptionPlan, SubscriptionStatus,
    VenueStatus, WorkspaceStatus, OrderStatus, PaymentStatus,
    PaymentMethod, PaymentGateway, OrderType, OrderSource,
    TableStatus, NotificationType, TransactionType, FeedbackType,
    PriceRange, SpiceLevel, Priority
)

# =============================================================================
# BASE MODELS
# =============================================================================
from app.models.base import (
    BaseSchema, BaseDTO, TimestampMixin,
    VenueLocation, VenueOperatingHours
)

# =============================================================================
# DATABASE ENTITIES
# =============================================================================
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

# =============================================================================
# WORKSPACE DTOs
# =============================================================================
from app.models.workspace import (
    WorkspaceCreateDTO, WorkspaceUpdateDTO, WorkspaceResponseDTO
)

# =============================================================================
# USER DTOs
# =============================================================================
from app.models.user import (
    UserCreateDTO, AdminUserCreateDTO, UserLoginDTO,
    UserUpdateDTO, UserResponseDTO
)

# =============================================================================
# VENUE DTOs
# =============================================================================
from app.models.venue import (
    VenueCreateDTO, VenueUpdateDTO, VenueResponseDTO,
    VenuePublicInfoDTO, VenueWorkspaceListDTO
)

# =============================================================================
# MENU DTOs
# =============================================================================
from app.models.menu import (
    MenuCategoryCreateDTO, MenuCategoryUpdateDTO, MenuCategoryResponseDTO,
    MenuItemCreateDTO, MenuItemUpdateDTO, MenuItemResponseDTO
)

# =============================================================================
# TABLE DTOs
# =============================================================================
from app.models.table import (
    TableAreaCreateDTO, TableAreaUpdateDTO, TableAreaResponseDTO,
    TableCreateDTO, TableUpdateDTO, TableResponseDTO
)

# =============================================================================
# CUSTOMER DTOs
# =============================================================================
from app.models.customer import (
    CustomerCreateDTO, CustomerUpdateDTO, CustomerResponseDTO
)

# =============================================================================
# ORDER DTOs
# =============================================================================
from app.models.order import (
    OrderItemCreateDTO, OrderItemResponseDTO,
    OrderCreateDTO, PublicOrderCreateDTO, OrderUpdateDTO,
    OrderResponseDTO, OrderCreationResponseDTO, OrderValidationResponseDTO
)

# =============================================================================
# ROLE DTOs
# =============================================================================
from app.models.role import (
    RoleCreateDTO, RoleUpdateDTO, RoleResponseDTO,
    RoleFiltersDTO, RolePermissionMappingDTO, RoleAssignmentDTO,
    RoleStatisticsDTO, BulkPermissionAssignmentDTO, SetupRoleDTO
)

# =============================================================================
# PERMISSION DTOs
# =============================================================================
from app.models.permission import (
    PermissionCreateDTO, PermissionUpdateDTO, PermissionResponseDTO,
    PermissionFiltersDTO, PermissionCategoryDTO, PermissionMatrixDTO,
    PermissionStatisticsDTO, BulkPermissionCreateDTO, BulkPermissionResponseDTO,
    PermissionCheckDTO, SetupPermissionDTO
)

# =============================================================================
# ANALYTICS DTOs
# =============================================================================
from app.models.analytics import (
    SalesAnalyticsDTO, VenueAnalyticsDTO, DashboardStatsDTO,
    DashboardDataDTO, SuperAdminDashboardDTO, AdminDashboardDTO,
    OperatorDashboardDTO
)

# =============================================================================
# COMMON DTOs
# =============================================================================
from app.models.common import (
    # Response DTOs
    AuthTokenDTO, TokenDTO, ApiResponseDTO, SimpleApiResponseDTO,
    PaginatedResponseDTO, ErrorResponseDTO,
    # Auth DTOs
    RefreshTokenRequest, ChangePasswordRequest, GetSaltRequest,
    ClientHashedLoginRequest,
    # Workspace Registration DTOs
    WorkspaceRegistrationDTO, WorkspaceRegistrationResponseDTO,
    WorkspaceOnboardingResponseDTO,
    # QR and Public Access DTOs
    QRCodeDataDTO, MenuPublicAccessDTO, VenueOperatingStatusDTO,
    # File Upload DTOs
    ImageUploadResponseDTO, BulkImageUploadResponseDTO,
    # Utility DTOs
    RepositoryFiltersDTO, NameAvailabilityDTO, ValidationResultDTO,
    SystemSetupDTO, SetupResponseDTO,
    # Legacy Compatibility
    ApiResponse, PaginatedResponse, ErrorResponse
)

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    'UserRole', 'BusinessType', 'SubscriptionPlan', 'SubscriptionStatus',
    'VenueStatus', 'WorkspaceStatus', 'OrderStatus', 'PaymentStatus',
    'PaymentMethod', 'PaymentGateway', 'OrderType', 'OrderSource',
    'TableStatus', 'NotificationType', 'TransactionType', 'FeedbackType',
    'PriceRange', 'SpiceLevel', 'Priority',
    
    # Base Models
    'BaseSchema', 'BaseDTO', 'TimestampMixin',
    'VenueLocation', 'VenueOperatingHours',
    
    # Database Entities
    'Workspace', 'User', 'Venue', 'MenuCategory', 'MenuItem',
    'Table', 'TableArea', 'Customer', 'Order', 'OrderItem',
    'Role', 'Permission', 'Transaction', 'Notification', 'Review',
    
    # Workspace DTOs
    'WorkspaceCreateDTO', 'WorkspaceUpdateDTO', 'WorkspaceResponseDTO',
    
    # User DTOs
    'UserCreateDTO', 'AdminUserCreateDTO', 'UserLoginDTO',
    'UserUpdateDTO', 'UserResponseDTO',
    
    # Venue DTOs
    'VenueCreateDTO', 'VenueUpdateDTO', 'VenueResponseDTO',
    'VenuePublicInfoDTO', 'VenueWorkspaceListDTO',
    
    # Menu DTOs
    'MenuCategoryCreateDTO', 'MenuCategoryUpdateDTO', 'MenuCategoryResponseDTO',
    'MenuItemCreateDTO', 'MenuItemUpdateDTO', 'MenuItemResponseDTO',
    
    # Table DTOs
    'TableAreaCreateDTO', 'TableAreaUpdateDTO', 'TableAreaResponseDTO',
    'TableCreateDTO', 'TableUpdateDTO', 'TableResponseDTO',
    
    # Customer DTOs
    'CustomerCreateDTO', 'CustomerUpdateDTO', 'CustomerResponseDTO',
    
    # Order DTOs
    'OrderItemCreateDTO', 'OrderItemResponseDTO',
    'OrderCreateDTO', 'PublicOrderCreateDTO', 'OrderUpdateDTO',
    'OrderResponseDTO', 'OrderCreationResponseDTO', 'OrderValidationResponseDTO',
    
    # Role DTOs
    'RoleCreateDTO', 'RoleUpdateDTO', 'RoleResponseDTO',
    'RoleFiltersDTO', 'RolePermissionMappingDTO', 'RoleAssignmentDTO',
    'RoleStatisticsDTO', 'BulkPermissionAssignmentDTO', 'SetupRoleDTO',
    
    # Permission DTOs
    'PermissionCreateDTO', 'PermissionUpdateDTO', 'PermissionResponseDTO',
    'PermissionFiltersDTO', 'PermissionCategoryDTO', 'PermissionMatrixDTO',
    'PermissionStatisticsDTO', 'BulkPermissionCreateDTO', 'BulkPermissionResponseDTO',
    'PermissionCheckDTO', 'SetupPermissionDTO',
    
    # Analytics DTOs
    'SalesAnalyticsDTO', 'VenueAnalyticsDTO', 'DashboardStatsDTO',
    'DashboardDataDTO', 'SuperAdminDashboardDTO', 'AdminDashboardDTO',
    'OperatorDashboardDTO',
    
    # Common DTOs
    'AuthTokenDTO', 'TokenDTO', 'ApiResponseDTO', 'SimpleApiResponseDTO',
    'PaginatedResponseDTO', 'ErrorResponseDTO',
    'RefreshTokenRequest', 'ChangePasswordRequest', 'GetSaltRequest',
    'ClientHashedLoginRequest',
    'WorkspaceRegistrationDTO', 'WorkspaceRegistrationResponseDTO',
    'WorkspaceOnboardingResponseDTO',
    'QRCodeDataDTO', 'MenuPublicAccessDTO', 'VenueOperatingStatusDTO',
    'ImageUploadResponseDTO', 'BulkImageUploadResponseDTO',
    'RepositoryFiltersDTO', 'NameAvailabilityDTO', 'ValidationResultDTO',
    'SystemSetupDTO', 'SetupResponseDTO',
    'ApiResponse', 'PaginatedResponse', 'ErrorResponse',
]
