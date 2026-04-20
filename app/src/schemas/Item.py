from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ItemBase(BaseModel):
    """Base item schema"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: int = Field(..., description="Category ID this item belongs to")
    workspace_id: int = Field(..., description="Workspace ID this item belongs to")
    price: float = Field(..., ge=0, description="Price in INR")
    is_available: bool = True
    is_vegetarian: Optional[bool] = Field(None, description="True = Veg, False = Non-Veg, None = Not Applicable (Retail)")


class ItemCreate(ItemBase):
    """Create item schema"""
    image_url: Optional[str] = None
    sort_order: int = 0


class ItemUpdate(BaseModel):
    """Update item schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[float] = Field(None, ge=0)
    is_available: Optional[bool] = None
    is_vegetarian: Optional[bool] = None
    image_url: Optional[str] = None
    sort_order: Optional[int] = None


class ItemResponse(ItemBase):
    """Item response schema"""
    id: int
    image_url: Optional[str] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
