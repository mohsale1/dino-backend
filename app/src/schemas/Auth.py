from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
    jwt_enabled: bool = True


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)


class SignupRequest(BaseModel):
    """Workspace + persona + admin user registration in one request."""
    # Workspace
    workspace_name: str = Field(..., min_length=1, max_length=200)
    workspace_description: Optional[str] = Field(None, max_length=500)
    referral_email: Optional[EmailStr] = None

    # Persona
    persona_name: str = Field(..., min_length=1, max_length=200)
    persona_type: int = Field(default=0, ge=0, le=1)
    order_type: int = Field(default=0, ge=0, le=1)
    persona_address: Optional[str] = Field(None, max_length=500)
    persona_city: Optional[str] = Field(None, max_length=100)
    persona_state: Optional[str] = Field(None, max_length=100)
    persona_country: Optional[str] = Field(None, max_length=100)
    persona_postal_code: Optional[str] = Field(None, max_length=20)
    persona_phone: Optional[str] = Field(None, max_length=30, pattern=r'^\+?[0-9\s\-\(\)]{7,30}$')
    persona_email: Optional[EmailStr] = None

    # Admin user
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)
    admin_first_name: str = Field(..., min_length=1, max_length=100)
    admin_last_name: str = Field(..., min_length=1, max_length=100)
    admin_phone: Optional[str] = Field(None, max_length=30, pattern=r'^\+?[0-9\s\-\(\)]{7,30}$')

    @field_validator('admin_password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class SignupResponse(BaseModel):
    workspace: Dict[str, Any]
    persona: Dict[str, Any]
    user: Dict[str, Any]
    message: str
