from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category_id: int
    price: float = Field(..., ge=0)
    is_available: bool = True
    is_vegetarian: Optional[bool] = None


class ItemCreate(ItemBase):
    persona_id: int
    image_url: Optional[str] = None


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category_id: Optional[int] = None
    price: Optional[float] = Field(None, ge=0)
    is_available: Optional[bool] = None
    is_vegetarian: Optional[bool] = None
    image_url: Optional[str] = None


class ItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    category_id: int
    persona_id: int
    price: float
    is_available: bool
    is_vegetarian: Optional[bool] = None
    image_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
