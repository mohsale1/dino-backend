"""
System Settings Routes
Endpoints for managing system-wide settings
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.base.BaseSchema import BaseResponse
from src.system.middleware.RoleCheck import SystemPermissionCheck
from src.system.services.Settings import SettingsService
from src.schemas.HomePageInfo import HomePageInfoUpdateSchema
from src.config.Database import get_db

router = APIRouter(prefix="/settings", tags=["System Settings"])


@router.get("/homepage", response_model=BaseResponse)
async def get_homepage_settings(db: AsyncSession = Depends(get_db)):
    """
    Get home page settings (Public endpoint)
    Anyone can view home page settings
    """
    try:
        service = SettingsService(db)
        homepage_info = await service.get_homepage_info()

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


@router.put("/homepage", response_model=BaseResponse, dependencies=[Depends(SystemPermissionCheck.require('settings:update'))])
async def update_homepage_settings(data: HomePageInfoUpdateSchema, db: AsyncSession = Depends(get_db)):
    """
    Update home page settings (SuperAdmin only)

    Body Parameters:
    - contact: Contact information (email, phone, address, etc.)
    - testimonials: Testimonials section configuration
    - stats: Stats section configuration
    """
    try:
        service = SettingsService(db)
        updated_info = await service.update_homepage_info(data.model_dump(exclude_none=True))

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
async def get_company_info(db: AsyncSession = Depends(get_db)):
    """Get contact information via the legacy /company endpoint (Public endpoint)"""
    try:
        service = SettingsService(db)
        homepage_info = await service.get_homepage_info()

        return {
            "success": True,
            "message": "Company information retrieved successfully",
            "data": homepage_info.get('contact', {})
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve company information: {str(e)}"
        )


@router.get("/homepage/contact", response_model=BaseResponse)
async def get_contact_info(db: AsyncSession = Depends(get_db)):
    """Get contact information (Public endpoint)"""
    try:
        service = SettingsService(db)
        homepage_info = await service.get_homepage_info()

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
