"""
Home Page Routes
Public endpoints for home page data stored in the homepage_info table.

The homepage_info table contains:
  - stats        : array of stat objects
  - testimonials : array of testimonial objects
  - contact      : contact information object
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.HomePage import HomePageService
from src.config.Database import get_db

router = APIRouter(prefix="/home", tags=["Home Page"])


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class StatItem(BaseModel):
    """Schema for a single stat item."""
    title: str = Field(..., description="Stat title")
    value: str = Field(..., description="Display value as string")
    number: float = Field(..., description="Numeric value (supports decimals)")
    suffix: str = Field(default="+", description="Suffix to display (e.g., '+', 'K', 'M', '%')")
    label: str = Field(..., description="Label for the stat")
    icon: str = Field(..., description="Icon name (e.g., 'restaurant', 'shopping_cart')")


class StatsUpdate(BaseModel):
    """Schema for updating stats array."""
    stats: List[StatItem] = Field(..., description="Array of stat objects")


class TestimonialItem(BaseModel):
    """Schema for a single testimonial."""
    name: str = Field(..., min_length=2, max_length=100, description="Customer name")
    role: Optional[str] = Field(None, max_length=50, description="Customer role/title")
    restaurant: Optional[str] = Field(None, max_length=100, description="Restaurant name")
    location: Optional[str] = Field(None, max_length=100, description="Location (city, state)")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    comment: str = Field(..., min_length=10, max_length=1000, description="Testimonial comment")
    avatar: Optional[str] = Field(None, max_length=500, description="Avatar URL or initials")
    created_at: Optional[str] = Field(None, description="Creation timestamp")

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class TestimonialsUpdate(BaseModel):
    """Schema for updating testimonials array."""
    testimonials: List[TestimonialItem] = Field(..., description="Array of testimonial objects")


class ContactInfo(BaseModel):
    """Schema for contact information."""
    email: Optional[str] = Field(None, max_length=100, description="Contact email")
    phone: Optional[str] = Field(None, max_length=20, description="Contact phone")
    address: Optional[str] = Field(None, max_length=500, description="Street address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=50, description="State/Province")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal/ZIP code")


class ContactInfoUpdate(BaseModel):
    """Schema for updating contact information."""
    contact: ContactInfo = Field(..., description="Contact information object")


class HomePageDataUpdate(BaseModel):
    """Schema for updating entire homepage data."""
    stats: Optional[List[StatItem]] = Field(None, description="Stats array")
    testimonials: Optional[List[TestimonialItem]] = Field(None, description="Testimonials array")
    contact: Optional[ContactInfo] = Field(None, description="Contact information")


# ============================================================================
# GET ENDPOINTS (Public - no authentication required)
# ============================================================================

@router.get("/stats")
async def get_home_stats(db: AsyncSession = Depends(get_db)):
    """
    Get home page statistics from the homepage_info table.

    Public endpoint - no authentication required.
    """
    service = HomePageService(db)
    stats = await service.get_stats()

    return {
        "success": True,
        "message": "Home page stats retrieved successfully",
        "data": stats,
    }


@router.get("/testimonials")
async def get_testimonials(
    limit: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get customer testimonials from the homepage_info table.

    Public endpoint - no authentication required.

    Query Parameters:
        - limit: Maximum number of testimonials to return (optional)
    """
    service = HomePageService(db)
    testimonials = await service.get_testimonials(limit=limit)

    return {
        "success": True,
        "message": "Testimonials retrieved successfully",
        "data": testimonials,
    }


@router.get("/contact")
async def get_contact_info(db: AsyncSession = Depends(get_db)):
    """
    Get contact information from the homepage_info table.

    Public endpoint - no authentication required.
    """
    service = HomePageService(db)
    contact = await service.get_contact_info()

    return {
        "success": True,
        "message": "Contact information retrieved successfully",
        "data": contact,
    }


@router.get("/all")
async def get_all_home_data(db: AsyncSession = Depends(get_db)):
    """
    Get all home page data in one call from the homepage_info table.

    Public endpoint - no authentication required.
    """
    service = HomePageService(db)
    data = await service.get_all_home_data()

    return {
        "success": True,
        "message": "Home page data retrieved successfully",
        "data": data,
    }


# ============================================================================
# PUT ENDPOINTS (Admin only)
# ============================================================================

@router.put("/stats", dependencies=[Depends(ApplicationPermissionCheck.require('homepage:update'))])
async def update_stats(
    data: StatsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update stats array in the homepage_info table. Admin only."""
    try:
        service = HomePageService(db)
        stats_list = [stat.model_dump() for stat in data.stats]
        result = await service.update_stats(stats_list)

        return {
            "success": True,
            "message": "Stats updated successfully",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/testimonials", dependencies=[Depends(ApplicationPermissionCheck.require('homepage:update'))])
async def update_testimonials(
    data: TestimonialsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update testimonials array in the homepage_info table. Admin only."""
    try:
        service = HomePageService(db)
        testimonials_list = [t.model_dump() for t in data.testimonials]
        result = await service.update_testimonials(testimonials_list)

        return {
            "success": True,
            "message": "Testimonials updated successfully",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/contact", dependencies=[Depends(ApplicationPermissionCheck.require('homepage:update'))])
async def update_contact_info(
    data: ContactInfoUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update contact information in the homepage_info table. Admin only."""
    try:
        service = HomePageService(db)
        result = await service.update_contact_info(data.contact.model_dump(exclude_none=True))

        return {
            "success": True,
            "message": "Contact information updated successfully",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/all", dependencies=[Depends(ApplicationPermissionCheck.require('homepage:update'))])
async def update_all_homepage_data(
    data: HomePageDataUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update entire homepage_info document (partial updates supported). Admin only."""
    try:
        service = HomePageService(db)

        update_data: Dict[str, Any] = {}
        if data.stats is not None:
            update_data["stats"] = [stat.model_dump() for stat in data.stats]
        if data.testimonials is not None:
            update_data["testimonials"] = [t.model_dump() for t in data.testimonials]
        if data.contact is not None:
            update_data["contact"] = data.contact.model_dump(exclude_none=True)

        result = await service.update_all_homepage_data(update_data)

        return {
            "success": True,
            "message": "Homepage data updated successfully",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
