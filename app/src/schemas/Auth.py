from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginResponse(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: dict
    jwt_enabled: bool = True


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)


class SignupRequest(BaseModel):
    """Workspace + persona + admin user registration in one request."""
    # Workspace
    workspace_name: str = Field(..., min_length=1, max_length=200)
    workspace_description: Optional[str] = None
    owner_referred_by: Optional[int] = None

    # Persona
    persona_name: str = Field(..., min_length=1, max_length=200)
    persona_type: int = Field(default=0, ge=0, le=1)
    order_type: int = Field(default=0, ge=0, le=1)
    persona_address: Optional[str] = None
    persona_city: Optional[str] = None
    persona_state: Optional[str] = None
    persona_country: Optional[str] = None
    persona_postal_code: Optional[str] = None
    persona_phone: Optional[str] = None
    persona_email: Optional[str] = None

    # Admin user
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=6)
    admin_first_name: str = Field(..., min_length=1, max_length=100)
    admin_last_name: str = Field(..., min_length=1, max_length=100)
    admin_phone: Optional[str] = None


class SignupResponse(BaseModel):
    workspace: dict
    persona: dict
    user: dict
    message: str
