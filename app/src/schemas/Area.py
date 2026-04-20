from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AreaBase(BaseModel):
    """Base area schema"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    workspace_id: int = Field(..., description="Workspace ID this area belongs to")
    is_available: bool = True


class AreaCreate(AreaBase):
    """Create area schema"""
    persona_id: Optional[int] = None


class AreaUpdate(BaseModel):
    """Update area schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_available: Optional[bool] = None
    persona_id: Optional[int] = None


class AreaResponse(AreaBase):
    """Area response schema"""
    id: int
    persona_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
