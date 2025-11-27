"""
Request/Response DTOs - Compatibility Layer
Re-exports all DTOs for backward compatibility with imports
"""

# User DTOs
from app.models.user import (
    UserCreateDTO, AdminUserCreateDTO, UserLoginDTO,
    UserUpdateDTO, UserResponseDTO
)

# Venue DTOs
from app.models.venue import (
    VenueCreateDTO, VenueUpdateDTO, VenueResponseDTO,
    VenuePublicInfoDTO, VenueWorkspaceListDTO
)

# Workspace DTOs
from app.models.workspace import (
    WorkspaceCreateDTO, WorkspaceUpdateDTO, WorkspaceResponseDTO
)

# Menu DTOs
from app.models.menu import (
    MenuCategoryCreateDTO, MenuCategoryUpdateDTO, MenuCategoryResponseDTO,
    MenuItemCreateDTO, MenuItemUpdateDTO, MenuItemResponseDTO
)

# Table DTOs
from app.models.table import (
    TableAreaCreateDTO, TableAreaUpdateDTO, TableAreaResponseDTO,
    TableCreateDTO, TableUpdateDTO, TableResponseDTO
)

# Customer DTOs
from app.models.customer import (
    CustomerCreateDTO, CustomerUpdateDTO, CustomerResponseDTO
)

# Order DTOs
from app.models.order import (
    OrderItemCreateDTO, OrderItemResponseDTO,
    OrderCreateDTO, PublicOrderCreateDTO, OrderUpdateDTO,
    OrderResponseDTO, OrderCreationResponseDTO, OrderValidationResponseDTO
)

# Role DTOs
from app.models.role import (
    RoleCreateDTO, RoleUpdateDTO, RoleResponseDTO,
    RoleFiltersDTO, RolePermissionMappingDTO, RoleAssignmentDTO,
    RoleStatisticsDTO, BulkPermissionAssignmentDTO, SetupRoleDTO
)

# Permission DTOs
from app.models.permission import (
    PermissionCreateDTO, PermissionUpdateDTO, PermissionResponseDTO,
    PermissionFiltersDTO, PermissionCategoryDTO, PermissionMatrixDTO,
    PermissionStatisticsDTO, BulkPermissionCreateDTO, BulkPermissionResponseDTO,
    PermissionCheckDTO, SetupPermissionDTO
)

# Analytics DTOs
from app.models.analytics import (
    SalesAnalyticsDTO, VenueAnalyticsDTO, DashboardStatsDTO,
    DashboardDataDTO, SuperAdminDashboardDTO, AdminDashboardDTO,
    OperatorDashboardDTO
)

# Common DTOs
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

__all__ = [
    # User DTOs
    'UserCreateDTO', 'AdminUserCreateDTO', 'UserLoginDTO',
    'UserUpdateDTO', 'UserResponseDTO',
    
    # Venue DTOs
    'VenueCreateDTO', 'VenueUpdateDTO', 'VenueResponseDTO',
    'VenuePublicInfoDTO', 'VenueWorkspaceListDTO',
    
    # Workspace DTOs
    'WorkspaceCreateDTO', 'WorkspaceUpdateDTO', 'WorkspaceResponseDTO',
    
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