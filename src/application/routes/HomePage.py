"""
Home Page Routes
Public endpoints for home page data stored in homepage_info collection

The homepage_info collection contains:
- stats: array of stat objects
- testimonials: array of testimonial objects
- contact: contact information object
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from src.application.services.HomePage import HomePageService

router = APIRouter(prefix="/home", tags=["Home Page"])


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class StatItem(BaseModel):
    """Schema for a single stat item"""
    title: str = Field(..., description="Stat title")
    value: str = Field(..., description="Display value as string")
    number: float = Field(..., description="Numeric value (supports decimals)")
    suffix: str = Field(default="+", description="Suffix to display (e.g., '+', 'K', 'M', '%')")
    label: str = Field(..., description="Label for the stat")
    icon: str = Field(..., description="Icon name (e.g., 'restaurant', 'shopping_cart')")


class StatsUpdate(BaseModel):
    """Schema for updating stats array"""
    stats: List[StatItem] = Field(..., description="Array of stat objects")


class TestimonialItem(BaseModel):
    """Schema for a single testimonial"""
    name: str = Field(..., min_length=2, max_length=100, description="Customer name")
    role: Optional[str] = Field(None, max_length=50, description="Customer role/title")
    restaurant: Optional[str] = Field(None, max_length=100, description="Restaurant name")
    location: Optional[str] = Field(None, max_length=100, description="Location (city, state)")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    comment: str = Field(..., min_length=10, max_length=1000, description="Testimonial comment")
    avatar: Optional[str] = Field(None, max_length=500, description="Avatar URL or initials")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v


class TestimonialsUpdate(BaseModel):
    """Schema for updating testimonials array"""
    testimonials: List[TestimonialItem] = Field(..., description="Array of testimonial objects")


class ContactInfo(BaseModel):
    """Schema for contact information"""
    email: Optional[str] = Field(None, max_length=100, description="Contact email")
    phone: Optional[str] = Field(None, max_length=20, description="Contact phone")
    address: Optional[str] = Field(None, max_length=500, description="Street address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=50, description="State/Province")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal/ZIP code")


class ContactInfoUpdate(BaseModel):
    """Schema for updating contact information"""
    contact: ContactInfo = Field(..., description="Contact information object")


class HomePageDataUpdate(BaseModel):
    """Schema for updating entire homepage data"""
    stats: Optional[List[StatItem]] = Field(None, description="Stats array")
    testimonials: Optional[List[TestimonialItem]] = Field(None, description="Testimonials array")
    contact: Optional[ContactInfo] = Field(None, description="Contact information")

# ============================================================================
# GET ENDPOINTS (Public - no authentication required)
# ============================================================================

@router.get("/stats")
async def get_home_stats():
    """
    Get home page statistics from homepage_info collection
    
    Public endpoint - no authentication required
    
    Returns:
        {
            "success": true,
            "message": "Home page stats retrieved successfully",
            "data": [
                {
                    "title": "Active Restaurants",
                    "value": "1",
                    "number": 1,
                    "suffix": "+",
                    "label": "Active Restaurants",
                    "icon": "restaurant"
                },
                ...
            ]
        }
    """
    service = HomePageService()
    stats = service.get_stats()
    
    return {
        "success": True,
        "message": "Home page stats retrieved successfully",
        "data": stats
    }


@router.get("/testimonials")
async def get_testimonials(limit: Optional[int] = None):
    """
    Get customer testimonials from homepage_info collection
    
    Public endpoint - no authentication required
    
    Query Parameters:
        - limit: Maximum number of testimonials to return (optional)
    
    Returns:
        {
            "success": true,
            "message": "Testimonials retrieved successfully",
            "data": [
                {
                    "name": "John Doe",
                    "role": "Restaurant Owner",
                    "restaurant": "Doe's Diner",
                    "location": "New York, NY",
                    "rating": 5,
                    "comment": "Great platform!",
                    "avatar": "JD",
                    "created_at": "2024-01-01T00:00:00Z"
                },
                ...
            ]
        }
    """
    service = HomePageService()
    testimonials = service.get_testimonials(limit=limit)
    
    return {
        "success": True,
        "message": "Testimonials retrieved successfully",
        "data": testimonials
    }


@router.get("/contact")
async def get_contact_info():
    """
    Get contact information from homepage_info collection
    
    Public endpoint - no authentication required
    
    Returns:
        {
            "success": true,
            "message": "Contact information retrieved successfully",
            "data": {
                "email": "contact@example.com",
                "phone": "+1234567890",
                "address": "123 Main St",
                "city": "New York",
                "state": "NY",
                "country": "USA",
                "postal_code": "10001"
            }
        }
    """
    service = HomePageService()
    contact = service.get_contact_info()
    
    return {
        "success": True,
        "message": "Contact information retrieved successfully",
        "data": contact
    }


@router.get("/all")
async def get_all_home_data():
    """
    Get all home page data in one call from homepage_info collection
    
    Public endpoint - no authentication required
    
    Returns:
        {
            "success": true,
            "message": "Home page data retrieved successfully",
            "data": {
                "stats": [...],
                "testimonials": [...],
                "contact": {...}
            }
        }
    """
    service = HomePageService()
    data = service.get_all_home_data()
    
    return {
        "success": True,
        "message": "Home page data retrieved successfully",
        "data": data
    }


# ============================================================================
# PUT ENDPOINTS (Public - no authentication required)
# ============================================================================

@router.put("/stats")
async def update_stats(data: StatsUpdate):
    """
    Update stats array in homepage_info collection
    
    Public endpoint - no authentication required
    
    Body Parameters:
        - stats: Array of stat objects
    
    Example:
        {
            "stats": [
                {
                    "title": "Active Restaurants",
                    "value": "1",
                    "number": 1,
                    "suffix": "+",
                    "label": "Active Restaurants",
                    "icon": "restaurant"
                },
                ...
            ]
        }
    
    Returns:
        {
            "success": true,
            "message": "Stats updated successfully",
            "data": [...]
        }
    """
    try:
        service = HomePageService()
        stats_list = [stat.model_dump() for stat in data.stats]
        result = service.update_stats(stats_list)
        
        return {
            "success": True,
            "message": "Stats updated successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/testimonials")
async def update_testimonials(data: TestimonialsUpdate):
    """
    Update testimonials array in homepage_info collection
    
    Public endpoint - no authentication required
    
    Body Parameters:
        - testimonials: Array of testimonial objects
    
    Example:
        {
            "testimonials": [
                {
                    "name": "John Doe",
                    "role": "Restaurant Owner",
                    "restaurant": "Doe's Diner",
                    "location": "New York, NY",
                    "rating": 5,
                    "comment": "Great platform!",
                    "avatar": "JD",
                    "created_at": "2024-01-01T00:00:00Z"
                },
                ...
            ]
        }
    
    Returns:
        {
            "success": true,
            "message": "Testimonials updated successfully",
            "data": [...]
        }
    """
    try:
        service = HomePageService()
        testimonials_list = [t.model_dump() for t in data.testimonials]
        result = service.update_testimonials(testimonials_list)
        
        return {
            "success": True,
            "message": "Testimonials updated successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/contact")
async def update_contact_info(data: ContactInfoUpdate):
    """
    Update contact information in homepage_info collection
    
    Public endpoint - no authentication required
    
    Body Parameters:
        - contact: Contact information object
    
    Example:
        {
            "contact": {
                "email": "contact@example.com",
                "phone": "+1234567890",
                "address": "123 Main St",
                "city": "New York",
                "state": "NY",
                "country": "USA",
                "postal_code": "10001"
            }
        }
    
    Returns:
        {
            "success": true,
            "message": "Contact information updated successfully",
            "data": {...}
        }
    """
    try:
        service = HomePageService()
        result = service.update_contact_info(data.contact.model_dump(exclude_none=True))
        
        return {
            "success": True,
            "message": "Contact information updated successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/all")
async def update_all_homepage_data(data: HomePageDataUpdate):
    """
    Update entire homepage_info document (partial updates supported)
    
    Public endpoint - no authentication required
    
    Body Parameters:
        - stats: Stats array (optional)
        - testimonials: Testimonials array (optional)
        - contact: Contact information (optional)
    
    Example:
        {
            "stats": [...],
            "testimonials": [...],
            "contact": {...}
        }
    
    Returns:
        {
            "success": true,
            "message": "Homepage data updated successfully",
            "data": {
                "stats": [...],
                "testimonials": [...],
                "contact": {...}
            }
        }
    """
    try:
        service = HomePageService()
        
        update_data = {}
        if data.stats is not None:
            update_data['stats'] = [stat.model_dump() for stat in data.stats]
        if data.testimonials is not None:
            update_data['testimonials'] = [t.model_dump() for t in data.testimonials]
        if data.contact is not None:
            update_data['contact'] = data.contact.model_dump(exclude_none=True)
        
        result = service.update_all_homepage_data(update_data)
        
        return {
            "success": True,
            "message": "Homepage data updated successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
