from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CategoryBase(BaseModel):
    """Base category schema"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    workspace_id: str = Field(..., description="Workspace ID this category belongs to")
    is_available: bool = True

class CategoryCreate(CategoryBase):
    """Create category schema"""
    pass

class CategoryUpdate(BaseModel):
    """Update category schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_available: Optional[bool] = None

class CategoryResponse(CategoryBase):
    """Category response schema"""
    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True