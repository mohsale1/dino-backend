"""
Home Page Info Schemas
Request/Response schemas for home page information

The homepage_info collection contains:
- stats: array of stat objects
- testimonials: array of testimonial objects
- contact: contact information object
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class StatItemSchema(BaseModel):
    """Schema for a single stat item"""
    title: str = Field(..., description="Stat title")
    value: str = Field(..., description="Display value as string")
    number: float = Field(..., description="Numeric value (supports decimals)")
    suffix: str = Field(default="+", description="Suffix to display")
    label: str = Field(..., description="Label for the stat")
    icon: str = Field(..., description="Icon name")


class TestimonialItemSchema(BaseModel):
    """Schema for a single testimonial"""
    name: str = Field(..., description="Customer name")
    role: Optional[str] = Field(None, description="Customer role/title")
    restaurant: Optional[str] = Field(None, description="Restaurant name")
    location: Optional[str] = Field(None, description="Location")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    comment: str = Field(..., description="Testimonial comment")
    avatar: Optional[str] = Field(None, description="Avatar URL or initials")
    created_at: Optional[str] = Field(None, description="Creation timestamp")


class ContactInfoSchema(BaseModel):
    """Schema for contact information"""
    email: Optional[str] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone")
    address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    country: Optional[str] = Field(None, description="Country")
    postal_code: Optional[str] = Field(None, description="Postal/ZIP code")

class HomePageInfoUpdateSchema(BaseModel):
    """Schema for updating homepage info (partial updates supported)"""
    stats: Optional[List[StatItemSchema]] = Field(None, description="Stats array")
    testimonials: Optional[List[TestimonialItemSchema]] = Field(None, description="Testimonials array")
    contact: Optional[ContactInfoSchema] = Field(None, description="Contact information")
