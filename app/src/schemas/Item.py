from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: int
    workspace_id: int
    price: float = Field(..., ge=0)
    is_available: bool = True
    is_vegetarian: Optional[bool] = None


class ItemCreate(ItemBase):
    image_url: Optional[str] = None


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[float] = Field(None, ge=0)
    is_available: Optional[bool] = None
    is_vegetarian: Optional[bool] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class ItemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category_id: int
    workspace_id: int
    price: float
    is_available: bool
    is_vegetarian: Optional[bool] = None
    image_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
