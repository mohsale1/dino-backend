from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RoleBase(BaseModel):
    """Base role schema"""
    name: str = Field(..., min_length=1, max_length=100)
    role_type: int = Field(..., ge=0, le=1, description="0=System, 1=Application")
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Create role schema"""
    pass


class RoleUpdate(BaseModel):
    """Update role schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    role_type: Optional[int] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None


class RoleResponse(BaseModel):
    """Role response schema"""
    id: int
    name: str
    role_type: int
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    permissions: Optional[list] = None

    class Config:
        from_attributes = True
