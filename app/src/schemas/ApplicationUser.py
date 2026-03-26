from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class ApplicationUserBase(BaseModel):
    """Base schema for application user"""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

class ApplicationUserCreate(ApplicationUserBase):
    """Schema for creating application user"""
    password: str = Field(..., min_length=8)
    role_id: str
    workspace_id: Optional[str] = None
    organization_id: Optional[str] = None

class ApplicationUserUpdate(BaseModel):
    """Schema for updating application user"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role_id: Optional[str] = None
    organization_id: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)

class ApplicationUserResponse(ApplicationUserBase):
    """Schema for application user response"""
    id: str
    role_id: str
    workspace_id: str
    organization_id: Optional[str] = None
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True