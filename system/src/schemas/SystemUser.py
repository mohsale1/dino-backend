from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class SystemUserBase(BaseModel):
    """Base system user schema"""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None


class SystemUserCreate(SystemUserBase):
    """Create system user schema"""
    password: str = Field(..., min_length=6)
    role_id: int


class SystemUserUpdate(BaseModel):
    """Update system user schema"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class SystemUserResponse(SystemUserBase):
    """System user response schema"""
    id: str
    role_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    role: Optional[dict] = None

    class Config:
        from_attributes = True
