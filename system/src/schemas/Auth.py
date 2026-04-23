from pydantic import BaseModel, EmailStr, Field
from typing import Optional


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
    jwt_enabled: bool = True


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
