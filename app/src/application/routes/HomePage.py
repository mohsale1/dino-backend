"""
HomePage router — public data API for the marketing/landing page.

GET endpoints are unauthenticated (public).
PUT endpoints require homepage:update permission (admin only).

Router prefix: /home  (registered as /api/v1/application/home/...)

Endpoints
---------
GET  /home/stats          — 4 stat cards: live DB counts + hardcoded uptime/satisfaction
GET  /home/testimonials   — approved reviews shaped as testimonials (?limit=N)
GET  /home/contact        — hardcoded company contact info
GET  /home/all            — stats + testimonials + contact in one call
PUT  /home/stats          — accepts updated stats payload, echoes it back (homepage:update)
PUT  /home/testimonials   — accepts updated testimonials payload, echoes it back (homepage:update)
PUT  /home/contact        — accepts updated contact payload, echoes it back (homepage:update)
PUT  /home/all            — accepts full homepage payload, echoes it back (homepage:update)
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.models.Customer import Customer
from src.models.Item import Item
from src.models.OrderDetail import OrderDetail
from src.models.Persona import Persona
from src.models.Review import Review
from src.models.User import User
from src.models.Workspace import Workspace

router = APIRouter(prefix="/home", tags=["HomePage"])

# ---------------------------------------------------------------------------
# Hardcoded company contact — change here when needed
# ---------------------------------------------------------------------------

_CONTACT_INFO: Dict[str, Any] = {
    "email": "contact@dino-order.com",
    "phone": "+91 98765 43210",
    "address": "123 Business Park",
    "city": "Mumbai",
    "state": "Maharashtra",
    "postal_code": "400001",
    "country": "India",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_stats(db: AsyncSession) -> List[Dict[str, Any]]:
    """Build the 4 stat cards from live DB counts + hardcoded values."""
    total_workspaces: int = (
        await db.execute(
            select(func.count(Workspace.id)).where(Workspace.is_active.is_(True))
        )
    ).scalar_one() or 0

    total_orders: int = (
        await db.execute(
            select(func.count(OrderDetail.id)).where(OrderDetail.is_active.is_(True))
        )
    ).scalar_one() or 0

    return [
        {
            "number": total_workspaces,
            "suffix": "+",
            "label": "Active Businesses",
            "icon": "business",
        },
        {
            "number": total_orders,
            "suffix": "+",
            "label": "Orders Processed",
            "icon": "shopping_cart",
        },
        {
            "number": 98,
            "suffix": "%",
            "label": "Customer Satisfaction",
            "icon": "thumb_up",
        },
        {
            "number": 99.9,
            "suffix": "%",
            "label": "Uptime",
            "icon": "cloud_done",
            "decimals": 1,
        },
    ]


async def _get_testimonials(db: AsyncSession, limit: int = 6) -> List[Dict[str, Any]]:
    """Return approved reviews shaped as testimonials."""
    stmt = (
        select(
            Review.id,
            Review.rating,
            Review.comment,
            Review.created_at,
            User.first_name,
            User.last_name,
            Persona.name.label("restaurant"),
        )
        .outerjoin(User, Review.user_id == User.id)
        .outerjoin(Persona, Review.persona_id == Persona.id)
        .where(
            Review.is_approved.is_(True),
            Review.is_active.is_(True),
        )
        .order_by(Review.created_at.desc())
        .limit(limit)
    )

    rows = (await db.execute(stmt)).all()

    testimonials = []
    for row in rows:
        first = row.first_name or ""
        last = row.last_name or ""
        name = f"{first} {last}".strip() or "Anonymous"
        testimonials.append({
            "name": name,
            "role": "Customer",
            "restaurant": row.restaurant or "",
            "rating": row.rating,
            "comment": row.comment or "",
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })

    return testimonials


# ---------------------------------------------------------------------------
# GET /home/stats
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=BaseResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Return 4 stat cards: live workspace/order counts + hardcoded satisfaction/uptime."""
    stats = await _get_stats(db)
    return {
        "success": True,
        "message": "Stats retrieved successfully",
        "data": stats,
    }


# ---------------------------------------------------------------------------
# GET /home/testimonials
# ---------------------------------------------------------------------------

@router.get("/testimonials", response_model=BaseResponse)
async def get_testimonials(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Return approved reviews shaped as testimonials."""
    testimonials = await _get_testimonials(db, limit=limit)
    return {
        "success": True,
        "message": "Testimonials retrieved successfully",
        "data": testimonials,
    }


# ---------------------------------------------------------------------------
# GET /home/contact
# ---------------------------------------------------------------------------

@router.get("/contact", response_model=BaseResponse)
async def get_contact():
    """Return company contact information."""
    return {
        "success": True,
        "message": "Contact info retrieved successfully",
        "data": _CONTACT_INFO,
    }


# ---------------------------------------------------------------------------
# GET /home/all
# ---------------------------------------------------------------------------

@router.get("/all", response_model=BaseResponse)
async def get_all(db: AsyncSession = Depends(get_db)):
    """Return stats, testimonials, and contact info in a single call."""
    stats = await _get_stats(db)
    testimonials = await _get_testimonials(db, limit=6)
    return {
        "success": True,
        "message": "Homepage data retrieved successfully",
        "data": {
            "stats": stats,
            "testimonials": testimonials,
            "contact": _CONTACT_INFO,
        },
    }


# ---------------------------------------------------------------------------
# PUT /home/stats  (homepage:update)
# ---------------------------------------------------------------------------

@router.put(
    "/stats",
    response_model=BaseResponse,
    dependencies=[Depends(ApplicationPermissionCheck.require("homepage:update"))],
)
async def update_stats(body: Dict[str, Any]):
    """Accept updated stats payload and echo it back."""
    stats = body.get("stats", [])
    return {
        "success": True,
        "message": "Stats updated successfully",
        "data": stats,
    }


# ---------------------------------------------------------------------------
# PUT /home/testimonials  (homepage:update)
# ---------------------------------------------------------------------------

@router.put(
    "/testimonials",
    response_model=BaseResponse,
    dependencies=[Depends(ApplicationPermissionCheck.require("homepage:update"))],
)
async def update_testimonials(body: Dict[str, Any]):
    """Accept updated testimonials payload and echo it back."""
    testimonials = body.get("testimonials", [])
    return {
        "success": True,
        "message": "Testimonials updated successfully",
        "data": testimonials,
    }


# ---------------------------------------------------------------------------
# PUT /home/contact  (homepage:update)
# ---------------------------------------------------------------------------

@router.put(
    "/contact",
    response_model=BaseResponse,
    dependencies=[Depends(ApplicationPermissionCheck.require("homepage:update"))],
)
async def update_contact(body: Dict[str, Any]):
    """Accept updated contact payload and echo it back."""
    contact = body.get("contact", {})
    return {
        "success": True,
        "message": "Contact info updated successfully",
        "data": contact,
    }


# ---------------------------------------------------------------------------
# PUT /home/all  (homepage:update)
# ---------------------------------------------------------------------------

@router.put(
    "/all",
    response_model=BaseResponse,
    dependencies=[Depends(ApplicationPermissionCheck.require("homepage:update"))],
)
async def update_all(body: Dict[str, Any]):
    """Accept full homepage payload and echo it back."""
    return {
        "success": True,
        "message": "Homepage data updated successfully",
        "data": body,
    }
