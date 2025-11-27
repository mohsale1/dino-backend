"""
Menu Models
Database entities and DTOs for menu categories and items
"""
from pydantic import Field
from typing import Optional, List
from datetime import datetime

from app.models.base import BaseSchema, BaseDTO, TimestampMixin
from app.models.enums import SpiceLevel


# =============================================================================
# DATABASE ENTITIES
# =============================================================================

class MenuCategory(BaseSchema, TimestampMixin):
    """Menu category collection schema"""
    id: str
    venue_id: str
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    image_url: Optional[str] = None
    is_active: bool = Field(default=True)


class MenuItem(BaseSchema, TimestampMixin):
    """Menu item collection schema"""
    id: str
    venue_id: str
    category_id: str
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    base_price: float = Field(..., gt=0)
    is_vegetarian: bool = Field(default=True)
    spice_level: SpiceLevel = SpiceLevel.MILD
    preparation_time_minutes: int = Field(..., ge=5, le=120)
    image_urls: List[str] = Field(default_factory=list)
    is_available: bool = Field(default=True)
    rating_total: float = Field(default=0.0, ge=0, description="Sum of all ratings")
    rating_count: int = Field(default=0, ge=0, description="Number of ratings received")
    average_rating: float = Field(default=0.0, ge=0, description="Calculated average rating")
    
    @property
    def calculated_average_rating(self) -> float:
        """Calculate average rating from rating_total and rating_count"""
        if self.rating_count == 0:
            return 0.0
        return round(self.rating_total / self.rating_count, 2)


# =============================================================================
# DTOs
# =============================================================================

class MenuCategoryCreateDTO(BaseDTO):
    """DTO for creating menu categories"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    venue_id: str


class MenuCategoryUpdateDTO(BaseDTO):
    """DTO for updating menu categories"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class MenuCategoryResponseDTO(BaseDTO):
    """Complete menu category response DTO"""
    id: str
    venue_id: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MenuItemCreateDTO(BaseDTO):
    """DTO for creating menu items"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    base_price: float = Field(..., gt=0)
    category_id: str
    venue_id: str
    is_vegetarian: bool = Field(default=True)
    spice_level: SpiceLevel = SpiceLevel.MILD
    preparation_time_minutes: int = Field(..., ge=5, le=120)


class MenuItemUpdateDTO(BaseDTO):
    """DTO for updating menu items"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    base_price: Optional[float] = Field(None, gt=0)
    category_id: Optional[str] = None
    is_vegetarian: Optional[bool] = None
    spice_level: Optional[SpiceLevel] = None
    preparation_time_minutes: Optional[int] = Field(None, ge=5, le=120)
    is_available: Optional[bool] = None


class MenuItemResponseDTO(BaseDTO):
    """Complete menu item response DTO"""
    id: str
    venue_id: str
    category_id: str
    name: str
    description: str
    base_price: float
    is_vegetarian: bool
    spice_level: SpiceLevel
    preparation_time_minutes: int
    image_urls: List[str] = Field(default_factory=list)
    is_available: bool
    rating_total: float = Field(description="Sum of all ratings")
    rating_count: int = Field(description="Number of ratings received")
    average_rating: float = Field(description="Calculated average rating")
    created_at: datetime
    updated_at: datetime
