from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime

class OrganizationBase(BaseModel):
    """Base organization schema"""
    name: str = Field(..., min_length=1, max_length=200, description="Organization name")
    description: Optional[str] = None
    workspace_id: str = Field(..., description="Workspace ID this organization belongs to")
    organization_type: int = Field(0, ge=0, le=1, description="0=FOOD, 1=NON_FOOD")
    order_type: int = Field(0, ge=0, le=1, description="0=Online, 1=Manual (Counter)")

class OrganizationCreate(OrganizationBase):
    """Create organization schema"""
    pass

class OrganizationUpdate(BaseModel):
    """Update organization schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    organization_type: Optional[int] = Field(None, ge=0, le=1)
    order_type: Optional[int] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None
    is_open: Optional[bool] = None

class OrganizationStatusUpdate(BaseModel):
    """Schema for toggling organization open/closed status"""
    is_open: bool
    workspace_id: str

class OrganizationResponse(OrganizationBase):
    """Organization response schema"""
    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True
