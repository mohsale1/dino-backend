from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime

class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str = Field(..., min_length=6)

class LoginResponse(BaseModel):
    """Login response schema"""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: dict
    jwt_enabled: Optional[bool] = True

class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    """Refresh token response schema"""
    access_token: str
    token_type: str = "bearer"

class ChangePasswordRequest(BaseModel):
    """Change password request schema"""
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)

class OrganizationSignupData(BaseModel):
    """Organization data for signup"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    organization_type: int = Field(0, ge=0, le=1, description="0=FOOD, 1=NON_FOOD")
    order_type: int = Field(0, ge=0, le=1, description="0=Online, 1=Manual (Counter)")

class AdminUserSignupData(BaseModel):
    """Admin user data for signup"""
    email: EmailStr
    password: str = Field(..., min_length=6)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None

class SignupRequest(BaseModel):
    """Signup request schema"""
    referral_code: str = Field(..., min_length=4, max_length=4, description="4-digit referral code from system user")
    workspace_name: str = Field(..., min_length=1, max_length=200)
    workspace_description: Optional[str] = None
    
    # Billing Information
    billing_name: Optional[str] = None
    billing_email: Optional[EmailStr] = None
    billing_phone: Optional[str] = None
    billing_address: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_country: Optional[str] = None
    
    organization: OrganizationSignupData
    admin_user: AdminUserSignupData

class SignupResponse(BaseModel):
    """Signup response schema"""
    workspace: Dict[str, Any]
    organization: Dict[str, Any]
    admin_user: Dict[str, Any]
    message: str = "Signup successful"