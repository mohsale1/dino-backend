"""
System Settings Routes
Endpoints for managing system-wide settings
"""

from fastapi import APIRouter, HTTPException, status, Depends
from src.base.BaseSchema import BaseResponse
from src.system.middleware.RoleCheck import SystemRoleCheck
from src.system.services.Settings import SettingsService
from src.schemas.HomePageInfo import HomePageInfoUpdateSchema

router = APIRouter(prefix="/settings", tags=["System Settings"])


@router.get("/homepage", response_model=BaseResponse)
async def get_homepage_settings():
    """
    Get home page settings (Public endpoint)
    Anyone can view home page settings
    """
    try:
        service = SettingsService()
        homepage_info = service.get_homepage_info()
        
        return {
            "success": True,
            "message": "Home page settings retrieved successfully",
            "data": homepage_info
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve home page settings: {str(e)}"
        )


@router.put("/homepage", response_model=BaseResponse, dependencies=[Depends(SystemRoleCheck.require_super_admin)])
async def update_homepage_settings(data: HomePageInfoUpdateSchema):
    """
    Update home page settings (SuperAdmin only)
    
    Body Parameters:
    - company: Company information (name, tagline, description, etc.)
    - contact: Contact information (email, phone, address, etc.)
    - social_media: Social media links (facebook, twitter, instagram, etc.)
    - hero: Hero section configuration
    - features: Features section configuration
    - testimonials: Testimonials section configuration
    - stats: Stats section configuration
    - faq: FAQ section configuration
    - cta: CTA section configuration
    - seo: SEO information
    - theme: Theme colors
    - settings: General settings (buttons, maintenance mode, etc.)
    """
    try:
        service = SettingsService()
        updated_info = service.update_homepage_info(data.model_dump(exclude_none=True))
        
        return {
            "success": True,
            "message": "Home page settings updated successfully",
            "data": updated_info
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update home page settings: {str(e)}"
        )


@router.get("/homepage/company", response_model=BaseResponse)
async def get_company_info():
    """Get company information (Public endpoint)"""
    try:
        service = SettingsService()
        homepage_info = service.get_homepage_info()
        
        return {
            "success": True,
            "message": "Company information retrieved successfully",
            "data": homepage_info.get('company', {})
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve company information: {str(e)}"
        )


@router.get("/homepage/contact", response_model=BaseResponse)
async def get_contact_info():
    """Get contact information (Public endpoint)"""
    try:
        service = SettingsService()
        homepage_info = service.get_homepage_info()
        
        return {
            "success": True,
            "message": "Contact information retrieved successfully",
            "data": homepage_info.get('contact', {})
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve contact information: {str(e)}"
        )