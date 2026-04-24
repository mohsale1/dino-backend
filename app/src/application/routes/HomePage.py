"""
HomePage router — public data API for the marketing/landing page.
All endpoints are unauthenticated and return live data from the database.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.models.Customer import Customer
from src.models.Item import Item
from src.models.OrderDetail import OrderDetail
from src.models.Persona import Persona
from src.models.Review import Review
from src.models.Workspace import Workspace
from src.repositories.ReviewRepository import ReviewRepository

router = APIRouter(prefix="/homepage", tags=["HomePage"])


# ---------------------------------------------------------------------------
# GET /homepage/stats — live platform-wide statistics
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=BaseResponse)
async def get_homepage_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Return live platform-wide statistics:
    - total_workspaces: count of active workspaces
    - total_orders: count of active order_details
    - total_customers: count of active customers
    - total_items: count of active items
    - average_rating: average rating from all approved + active reviews
    """
    total_workspaces = (
        await db.execute(
            select(func.count(Workspace.id)).where(Workspace.is_active.is_(True))
        )
    ).scalar_one() or 0

    total_orders = (
        await db.execute(
            select(func.count(OrderDetail.id)).where(OrderDetail.is_active.is_(True))
        )
    ).scalar_one() or 0

    total_customers = (
        await db.execute(
            select(func.count(Customer.id)).where(Customer.is_active.is_(True))
        )
    ).scalar_one() or 0

    total_items = (
        await db.execute(
            select(func.count(Item.id)).where(Item.is_active.is_(True))
        )
    ).scalar_one() or 0

    review_repo = ReviewRepository(db)
    average_rating = await review_repo.get_global_average_rating()

    return {
        "success": True,
        "message": "Homepage stats retrieved successfully",
        "data": {
            "total_workspaces": total_workspaces,
            "total_orders": total_orders,
            "total_customers": total_customers,
            "total_items": total_items,
            "average_rating": average_rating,
        },
    }


# ---------------------------------------------------------------------------
# GET /homepage/reviews — latest approved reviews (public)
# ---------------------------------------------------------------------------

@router.get("/reviews", response_model=BaseResponse)
async def get_homepage_reviews(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Return latest approved + active reviews with user_name.
    Optionally filtered by workspace_id and/or persona_id.
    Ordered by created_at DESC.
    """
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id is required",
        )
    review_repo = ReviewRepository(db)
    reviews = await review_repo.get_approved_reviews(
        workspace_id=workspace_id,
        persona_id=persona_id,
        limit=limit,
    )
    return {
        "success": True,
        "message": "Homepage reviews retrieved successfully",
        "data": reviews,
    }


# ---------------------------------------------------------------------------
# GET /homepage/featured-personas — active open personas (public)
# ---------------------------------------------------------------------------

@router.get("/featured-personas", response_model=BaseResponse)
async def get_featured_personas(
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Return active, open, non-deactivated personas with their workspace name.
    Ordered by created_at DESC.
    """
    stmt = (
        select(
            Persona.id,
            Persona.name,
            Persona.description,
            Persona.persona_type,
            Persona.order_type,
            Persona.logo_url,
            Persona.address,
            Persona.city,
            Persona.state,
            Persona.country,
            Persona.postal_code,
            Persona.phone,
            Persona.email,
            Persona.is_open,
            Persona.is_deactivated,
            Persona.is_active,
            Persona.workspace_id,
            Persona.created_at,
            Persona.updated_at,
            Workspace.name.label("workspace_name"),
        )
        .join(Workspace, Persona.workspace_id == Workspace.id)
        .where(
            and_(
                Persona.is_active.is_(True),
                Persona.is_open.is_(True),
                Persona.is_deactivated.is_(False),
            )
        )
        .order_by(Persona.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.mappings().all()
    personas = [dict(r) for r in rows]

    return {
        "success": True,
        "message": "Featured personas retrieved successfully",
        "data": personas,
    }
