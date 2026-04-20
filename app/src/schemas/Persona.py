from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class PersonaBase(BaseModel):
    """Base persona schema"""
    name: str = Field(..., min_length=1, max_length=200, description="Persona name")
    description: Optional[str] = None
    workspace_id: Optional[int] = None
    organization_type: int = Field(0, ge=0, le=1, description="0=FOOD, 1=NON_FOOD")
    order_type: int = Field(0, ge=0, le=1, description="0=Online, 1=Manual (Counter)")


class PersonaCreate(PersonaBase):
    """Create persona schema"""
    pass


class PersonaUpdate(BaseModel):
    """Update persona schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    organization_type: Optional[int] = Field(None, ge=0, le=1)
    order_type: Optional[int] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None
    is_open: Optional[bool] = None


class PersonaStatusUpdate(BaseModel):
    """Schema for toggling persona open/closed status"""
    is_open: bool
    workspace_id: int


class PersonaResponse(PersonaBase):
    """Persona response schema"""
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    is_deactivated: bool
    is_open: bool
    logo_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True
