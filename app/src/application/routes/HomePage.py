"""
HomePage router — public data API + admin CRUD for homepage config.

Public endpoints (no auth):
  GET  /home/stats          — 4 stat cards (2 live counts + 2 from config)
  GET  /home/testimonials   — top 5 approved reviews
  GET  /home/contact        — contact info from DB
  GET  /home/all            — stats + testimonials + contact, parallelised

Admin endpoints (authenticated):
  GET  /home/config         — raw config row
  PUT  /home/config         — update any config field
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Homepage import HomepageService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError
from src.models.Review import Review
from src.models.User import User
from src.models.Workspace import Workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/home", tags=["HomePage"])


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class UpdateHomepageConfigRequest(BaseModel):
    # Contact
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=30)
    contact_address: Optional[str] = Field(None, max_length=500)
    contact_city: Optional[str] = Field(None, max_length=100)
    contact_state: Optional[str] = Field(None, max_length=100)
    contact_postal_code: Optional[str] = Field(None, max_length=20)
    contact_country: Optional[str] = Field(None, max_length=100)

    # Stat 1 — businesses
    stat_businesses_label: Optional[str] = Field(None, max_length=100)
    stat_businesses_suffix: Optional[str] = Field(None, max_length=10)
    stat_businesses_icon: Optional[str] = Field(None, max_length=100)

    # Stat 2 — orders
    stat_orders_label: Optional[str] = Field(None, max_length=100)
    stat_orders_suffix: Optional[str] = Field(None, max_length=10)
    stat_orders_icon: Optional[str] = Field(None, max_length=100)

    # Stat 3 — satisfaction
    stat_satisfaction_label: Optional[str] = Field(None, max_length=100)
    stat_satisfaction_suffix: Optional[str] = Field(None, max_length=10)
    stat_satisfaction_icon: Optional[str] = Field(None, max_length=100)
    satisfaction: Optional[int] = Field(None, ge=0, le=100)

    # Stat 4 — uptime
    stat_uptime_label: Optional[str] = Field(None, max_length=100)
    stat_uptime_suffix: Optional[str] = Field(None, max_length=10)
    stat_uptime_icon: Optional[str] = Field(None, max_length=100)
    uptime: Optional[str] = Field(None, max_length=10)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _get_testimonials(db: AsyncSession):
    """Top 5 most recent approved reviews — single JOIN query."""
    stmt = (
        select(
            Review.id,
            Review.rating,
            Review.comment,
            Review.created_at,
            User.first_name,
            User.last_name,
            Workspace.name.label("workspace_name"),
        )
        .outerjoin(User, Review.user_id == User.id)
        .join(Workspace, Review.workspace_id == Workspace.id)
        .where(
            Review.is_approved.is_(True),
            Review.is_active.is_(True),
            Workspace.is_active.is_(True),
        )
        .order_by(Review.created_at.desc())
        .limit(5)
    )
    rows = (await db.execute(stmt)).all()
    logger.debug("homepage.testimonials.fetched count=%s", len(rows))
    return [
        {
            "name": f"{row.first_name or ''} {row.last_name or ''}".strip() or "Anonymous",
            "role": "Customer",
            "rating": float(row.rating),
            "comment": row.comment or "",
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "workspace_name": row.workspace_name,
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Public — GET /home/stats
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=BaseResponse)
async def get_stats(request: Request, db: AsyncSession = Depends(get_db)):
    """Return 4 stat cards. Live counts computed in parallel, metadata from DB config."""
    ip = _client_ip(request)
    logger.info("homepage.stats.request ip=%s", ip)

    service = HomepageService(db)
    config = await service.get_config()
    stats = await service.get_stats(config)

    logger.info("homepage.stats.response ip=%s cards=%s", ip, len(stats))
    return {"success": True, "message": "Stats retrieved successfully", "data": stats}


# ---------------------------------------------------------------------------
# Public — GET /home/testimonials
# ---------------------------------------------------------------------------

@router.get("/testimonials", response_model=BaseResponse)
async def get_testimonials(request: Request, db: AsyncSession = Depends(get_db)):
    """Return top 5 most recent approved reviews as testimonials."""
    ip = _client_ip(request)
    logger.info("homepage.testimonials.request ip=%s", ip)

    testimonials = await _get_testimonials(db)

    logger.info("homepage.testimonials.response ip=%s count=%s", ip, len(testimonials))
    return {"success": True, "message": "Testimonials retrieved successfully", "data": testimonials}


# ---------------------------------------------------------------------------
# Public — GET /home/contact
# ---------------------------------------------------------------------------

@router.get("/contact", response_model=BaseResponse)
async def get_contact(request: Request, db: AsyncSession = Depends(get_db)):
    """Return company contact information from DB."""
    ip = _client_ip(request)
    logger.info("homepage.contact.request ip=%s", ip)

    config = await HomepageService(db).get_config()
    contact = HomepageService.get_contact(config)

    logger.info("homepage.contact.response ip=%s", ip)
    return {"success": True, "message": "Contact info retrieved successfully", "data": contact}


# ---------------------------------------------------------------------------
# Public — GET /home/all
# ---------------------------------------------------------------------------

@router.get("/all", response_model=BaseResponse)
async def get_all(request: Request, db: AsyncSession = Depends(get_db)):
    """Return stats, testimonials, and contact — all DB work parallelised."""
    ip = _client_ip(request)
    logger.info("homepage.all.request ip=%s", ip)

    service = HomepageService(db)
    config = await service.get_config()

    stats, testimonials = await asyncio.gather(
        service.get_stats(config),
        _get_testimonials(db),
    )
    contact = HomepageService.get_contact(config)

    logger.info(
        "homepage.all.response ip=%s stats=%s testimonials=%s",
        ip, len(stats), len(testimonials),
    )
    return {
        "success": True,
        "message": "Homepage data retrieved successfully",
        "data": {
            "stats": stats,
            "testimonials": testimonials,
            "contact": contact,
        },
    }


# ---------------------------------------------------------------------------
# Admin — GET /home/config
# ---------------------------------------------------------------------------

@router.get("/config", response_model=BaseResponse)
async def get_config(
    request: Request,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return the raw homepage config row for the admin UI."""
    user_id = current_user.get("id")
    logger.info("homepage.config.get.request user_id=%s", user_id)

    config = await HomepageService(db).get_config()

    logger.info("homepage.config.get.response user_id=%s", user_id)
    return {"success": True, "message": "Homepage config retrieved successfully", "data": config}


# ---------------------------------------------------------------------------
# Admin — PUT /home/config
# ---------------------------------------------------------------------------

@router.put("/config", response_model=BaseResponse)
async def update_config(
    request: Request,
    body: UpdateHomepageConfigRequest,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update homepage config fields. Only provided fields are updated."""
    user_id = current_user.get("id")
    data = body.model_dump(exclude_unset=True)

    if not data:
        logger.warning("homepage.config.update.empty_payload user_id=%s", user_id)
        raise BadRequestError("No fields provided to update")

    logger.info(
        "homepage.config.update.request user_id=%s fields=%s",
        user_id, list(data.keys()),
    )

    updated_config = await HomepageService(db).update_config(data)

    logger.info(
        "homepage.config.update.response user_id=%s fields=%s",
        user_id, list(data.keys()),
    )
    return {"success": True, "message": "Homepage config updated successfully", "data": updated_config}
