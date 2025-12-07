"""
Venue Models
Database entities and DTOs for venue management
"""
from pydantic import EmailStr, Field, validator
from typing import Optional, List, Dict
from datetime import datetime

from app.models.base import BaseSchema, BaseDTO, TimestampMixin, VenueLocation
from app.models.enums import PriceRange, SubscriptionPlan, SubscriptionStatus, VenueStatus, VenueType


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
    venue_type: Optional[VenueType] = Field(default=VenueType.RESTAURANT, description="Type of venue")
    price_range: PriceRange
    subscription_plan: SubscriptionPlan = SubscriptionPlan.BASIC
    is_active: bool = Field(default=True)
    is_open: bool = Field(default=True, description="Whether venue is currently open for orders")
    
    @validator('website')
    def validate_venue_website(cls, v):
        """Validate website URL - allow empty strings"""
        if v is None or v == "":
            return None
        if not v.startswith(('http://', 'https://')):
            v = f"https://{v}"
        return v


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
    venue_type: Optional[VenueType] = Field(default=VenueType.RESTAURANT, description="Type of venue")
    price_range: PriceRange
    subscription_plan: SubscriptionPlan = SubscriptionPlan.BASIC
    logo_url: Optional[str] = None
    is_open: bool = Field(default=True, description="Whether venue is open for orders")


class VenueUpdateDTO(BaseDTO):
    """DTO for updating venues"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    location: Optional[VenueLocation] = None
    phone: Optional[str] = Field(None, pattern="^[0-9]{10}$")
    email: Optional[EmailStr] = None
    logo_url: Optional[str] = None
    venue_type: Optional[VenueType] = None
    price_range: Optional[PriceRange] = None
    subscription_plan: Optional[SubscriptionPlan] = None
    is_active: Optional[bool] = None
    is_open: Optional[bool] = None


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
    venue_type: Optional[VenueType] = Field(default=VenueType.RESTAURANT, description="Type of venue")
    price_range: PriceRange
    subscription_plan: SubscriptionPlan
    is_active: bool
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
    created_at: datetime
    updated_at: datetime