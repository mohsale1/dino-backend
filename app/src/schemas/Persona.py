from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PersonaBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    persona_type: int = Field(default=0, ge=0, le=1)
    order_type: int = Field(default=0, ge=0, le=1)
    workspace_id: int


class PersonaCreate(PersonaBase):
    logo_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class PersonaUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    persona_type: Optional[int] = Field(None, ge=0, le=1)
    order_type: Optional[int] = Field(None, ge=0, le=1)
    logo_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    is_open: Optional[bool] = None
    is_deactivated: Optional[bool] = None


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

    class Config:
        from_attributes = True
