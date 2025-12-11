"""
User Models
Database entities and DTOs for user management
"""
from pydantic import EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

from app.models.base import BaseSchema, BaseDTO, TimestampMixin


# =============================================================================
# DATABASE ENTITY
# =============================================================================

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
    deleted: bool = Field(default=False, description="Soft delete flag - user is marked as deleted")
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


# =============================================================================
# DTOs
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
    """DTO for updating users - accepts camelCase"""
    firstName: Optional[str] = Field(None, min_length=1, max_length=50, alias="first_name")
    lastName: Optional[str] = Field(None, min_length=1, max_length=50, alias="last_name")
    phone: Optional[str] = Field(None, pattern="^[0-9]{10}$")
    isActive: Optional[bool] = Field(None, alias="is_active")
    
    class Config:
        populate_by_name = True


class UserResponseDTO(BaseDTO):
    """Complete user response DTO - camelCase for frontend"""
    id: str
    email: EmailStr
    phone: str = Field(default="", description="Phone number")
    firstName: str = Field(..., alias="first_name")
    lastName: str = Field(..., alias="last_name")
    role: str = Field(default="operator", description="Role name")
    workspaceId: Optional[str] = Field(None, alias="workspace_id")
    venueId: Optional[str] = Field(None, description="Active venue ID (first from venueIds)")
    venueIds: List[str] = Field(default_factory=list, alias="venue_ids")
    isActive: bool = Field(default=True, alias="is_active")
    isVerified: bool = Field(default=False, alias="is_verified")
    createdAt: datetime = Field(..., alias="created_at")
    updatedAt: datetime = Field(..., alias="updated_at")
    
    class Config:
        populate_by_name = True
        by_alias = True