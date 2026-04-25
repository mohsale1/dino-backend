from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PersonaBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    persona_type: int = Field(default=0, ge=0, le=1)
    order_type: int = Field(default=0, ge=0, le=1)


class PersonaCreate(PersonaBase):
    logo_url: Optional[str] = None
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=30, pattern=r'^\+?[0-9\s\-\(\)]{7,30}$')
    email: Optional[EmailStr] = None


class PersonaUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    persona_type: Optional[int] = Field(None, ge=0, le=1)
    order_type: Optional[int] = Field(None, ge=0, le=1)
    logo_url: Optional[str] = None
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=30, pattern=r'^\+?[0-9\s\-\(\)]{7,30}$')
    email: Optional[EmailStr] = None
    is_open: Optional[bool] = None


class PersonaResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    persona_type: int
    order_type: int
    workspace_id: int
    logo_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_open: bool
    is_deactivated: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
