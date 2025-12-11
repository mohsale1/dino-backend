"""
Common Models
Common DTOs and response models used across the application
"""
from pydantic import EmailStr, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.base import BaseDTO, VenueLocation
from app.models.enums import PriceRange, VenueStatus, OrderSource
from app.models.user import UserResponseDTO
from app.models.customer import CustomerCreateDTO
from app.models.order import OrderItemCreateDTO


# =============================================================================
# RESPONSE DTOs
# =============================================================================

class AuthTokenDTO(BaseDTO):
    """Authentication token response DTO"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: Optional[Any] = None  # Made optional - can be minimal user data or full UserResponseDTO


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


# =============================================================================
# AUTH REQUEST DTOs
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
# WORKSPACE REGISTRATION DTOs
# =============================================================================

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
    venue: Dict[str, Any]
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


class SystemSetupDTO(BaseDTO):
    """DTO for complete system setup"""
    permissions: List[Dict[str, Any]] = Field(default_factory=list)
    roles: List[Dict[str, Any]] = Field(default_factory=list)


class SetupResponseDTO(BaseDTO):
    """DTO for setup operation responses"""
    success: bool
    message: str
    created_permissions: int = 0
    created_roles: int = 0
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

# Keep these for backward compatibility with existing code
ApiResponse = ApiResponseDTO
PaginatedResponse = PaginatedResponseDTO
ErrorResponse = ErrorResponseDTO