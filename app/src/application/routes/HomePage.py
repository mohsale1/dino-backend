import asyncio
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.Homepage import HomepageService
from src.config.Utility import _client_ip
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.models.Review import Review
from src.models.User import User
from src.models.Workspace import Workspace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/home", tags=["HomePage"])

@router.get("/stats", response_model=BaseResponse)
async def get_stats(request: Request, db: AsyncSession = Depends(get_db)):
    """Return 4 stat cards. Live counts computed in parallel, metadata from DB config."""
    ip = _client_ip(request)
    logger.info("homepage.stats.request ip=%s", ip)
    try:
        service = HomepageService(db)
        config = await service.get_config()
        stats = await service.get_stats(config)
        logger.info("homepage.stats.response ip=%s cards=%s", ip, len(stats))
        return {"success": True, "message": "Stats retrieved successfully", "data": stats}
    except Exception as e:
        logger.error("homepage.stats.failed ip=%s error=%s", ip, str(e), exc_info=True)
        return {"success": False, "message": "Failed to retrieve stats", "error_code": "INTERNAL_ERROR"}


@router.get("/testimonials", response_model=BaseResponse)
async def get_testimonials(request: Request, db: AsyncSession = Depends(get_db)):
    """Return top 5 most recent approved reviews as testimonials."""
    ip = _client_ip(request)
    logger.info("homepage.testimonials.request ip=%s", ip)
    try:
        config = await HomepageService(db).get_config()
        testimonials = HomepageService.get_testimonials(config)
        logger.info("homepage.testimonials.response ip=%s count=%s", ip, len(testimonials))
        return {"success": True, "message": "Testimonials retrieved successfully", "data": testimonials}
    except Exception as e:
        logger.error("homepage.testimonials.failed ip=%s error=%s", ip, str(e), exc_info=True)
        return {"success": False, "message": "Failed to retrieve testimonials", "error_code": "INTERNAL_ERROR"}


@router.get("/contact", response_model=BaseResponse)
async def get_contact(request: Request, db: AsyncSession = Depends(get_db)):
    """Return company contact information from DB."""
    ip = _client_ip(request)
    logger.info("homepage.contact.request ip=%s", ip)
    try:
        config = await HomepageService(db).get_config()
        contact = HomepageService.get_contact(config)
        logger.info("homepage.contact.response ip=%s", ip)
        return {"success": True, "message": "Contact info retrieved successfully", "data": contact}
    except Exception as e:
        logger.error("homepage.contact.failed ip=%s error=%s", ip, str(e), exc_info=True)
        return {"success": False, "message": "Failed to retrieve contact info", "error_code": "INTERNAL_ERROR"}