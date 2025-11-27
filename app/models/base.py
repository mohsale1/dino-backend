"""
Base Models and Mixins
Common base classes and reusable components
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, time


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BaseDTO(BaseModel):
    """Base DTO with common configuration"""
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VenueLocation(BaseModel):
    """Venue location details"""
    address: str = Field(..., min_length=5, max_length=500)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=3, max_length=20)
    landmark: Optional[str] = Field(None, max_length=200)


class VenueOperatingHours(BaseModel):
    """Operating hours for a venue"""
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    is_open: bool = Field(default=True, description="Whether venue is open on this day")
    open_time: Optional[time] = Field(None, description="Opening time")
    close_time: Optional[time] = Field(None, description="Closing time")