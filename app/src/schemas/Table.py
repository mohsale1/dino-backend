from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TableBase(BaseModel):
    """Base table schema"""
    table_number: str = Field(..., min_length=1, max_length=50, description="Table number (e.g., T1, A-101)")
    area_id: str = Field(..., description="Area ID this table belongs to")
    workspace_id: str = Field(..., description="Workspace ID this table belongs to")
    capacity: int = Field(4, ge=1, description="Number of seats")
    status: str = Field("available", description="available, occupied, reserved, maintenance")

class TableCreate(TableBase):
    """Create table schema"""
    pass

class TableUpdate(BaseModel):
    """Update table schema"""
    table_number: Optional[str] = Field(None, min_length=1, max_length=50)
    capacity: Optional[int] = Field(None, ge=1)
    status: Optional[str] = None

class TableResponse(TableBase):
    """Table response schema"""
    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True