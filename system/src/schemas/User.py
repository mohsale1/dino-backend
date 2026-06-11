from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None


class UserCreate(UserBase):
    """Create user schema"""
    password: str = Field(..., min_length=6)
    role_id: int
    user_type: int = Field(default=0, ge=0, le=1, description="0=System, 1=Application")


class UserUpdate(BaseModel):
    """Update user schema"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    role_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    user_type: int
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role_id: int
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    role: Optional[dict] = None

    class Config:
        from_attributes = True
