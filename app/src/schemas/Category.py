from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoryBase(BaseModel):
    """Base category schema"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    workspace_id: int = Field(..., description="Workspace ID this category belongs to")
    is_available: bool = True


class CategoryCreate(CategoryBase):
    """Create category schema"""
    parent_id: Optional[int] = None
    image_url: Optional[str] = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    """Update category schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_available: Optional[bool] = None
    parent_id: Optional[int] = None
    image_url: Optional[str] = None
    sort_order: Optional[int] = None


class CategoryResponse(CategoryBase):
    """Category response schema"""
    id: int
    parent_id: Optional[int] = None
    image_url: Optional[str] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
