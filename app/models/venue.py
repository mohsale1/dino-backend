"""
Venue Models
Database entities and DTOs for venue management
"""
from pydantic import EmailStr, Field, validator
from typing import Optional, List, Dict
from datetime import datetime

from app.models.base import BaseSchema, BaseDTO, TimestampMixin, VenueLocation
from app.models.enums import PriceRange, SubscriptionPlan, SubscriptionStatus, VenueStatus


# =============================================================================
# DATABASE ENTITY
# =============================================================================

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


# =============================================================================
# DTOs
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
    is_open: bool = Field(default=False, description="Current operational status - true if status is 'active', false otherwise")
    subscription_status: SubscriptionStatus
    created_at: datetime
    updated_at: datetime