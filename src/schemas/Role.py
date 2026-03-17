from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class RoleBase(BaseModel):
    """Base role schema"""
    name: str = Field(..., min_length=1, max_length=100)
    role_type: int = Field(..., ge=0, le=1, description="0=System, 1=Application")
    description: Optional[str] = None
    permissions: List[str] = []

class RoleCreate(RoleBase):
    """Create role schema"""
    pass

class RoleUpdate(BaseModel):
    """Update role schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None

class RoleResponse(RoleBase):
    """Role response schema"""
    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True