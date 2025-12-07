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
    deleted: bool = Field(default=False, description="Soft delete flag - user is marked as deleted")
    is_verified: bool = Field(default=False)
    email_verified: bool = Field(default=False)
    phone_verified: bool = Field(default=False)
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime