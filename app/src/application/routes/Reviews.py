"""
Reviews router — CRUD and moderation endpoints for customer reviews.

Isolation contract
------------------
- workspace_id is ALWAYS sourced from the JWT (current_user) on protected endpoints.
- persona_id is REQUIRED on every protected endpoint (Query ge=1 or body Field ge=1).
- All write operations use a single DB round-trip — no pre-fetch SELECT before UPDATE/DELETE.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Review import ReviewService
from src.base.BaseSchema import BaseResponse, PaginatedResponse, PaginationMeta
from src.config.Database import get_db
from src.schemas.Review import ReviewCreate, ReviewUpdate

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_workspace(current_user: Dict[str, Any]) -> int:
    """Extract workspace_id from the JWT payload, raising 400 if absent."""
    wid = current_user.get("workspace_id")
    if not wid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id is missing from token",
        )
    return wid


# ---------------------------------------------------------------------------
# POST /reviews — create a review
# ---------------------------------------------------------------------------

@router.post("", response_model=BaseResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    body: ReviewCreate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:create")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new review.
    persona_id is required in the request body (ge=1).
    workspace_id and user_id are injected from the JWT.
    """
    wid = _require_workspace(current_user)

    data = body.model_dump()
    data["workspace_id"] = wid
    data["user_id"] = current_user.get("id")

    service = ReviewService(db)
    review = await service.create_review(data)
    return {"success": True, "message": "Review created successfully", "data": review}


# ---------------------------------------------------------------------------
# GET /reviews — paginated list (protected)
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse)
async def list_reviews(
    persona_id: int = Query(..., ge=1),
    is_approved: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated reviews scoped to the caller's workspace and the given persona.
    workspace_id is always resolved from the JWT — never accepted as a query param.
    """
    wid = _require_workspace(current_user)

    service = ReviewService(db)
    items, total, total_pages = await service.get_paginated_reviews(
        page=page,
        page_size=page_size,
        workspace_id=wid,
        persona_id=persona_id,
        is_approved=is_approved,
    )
    return {
        "success": True,
        "message": "Reviews retrieved successfully",
        "data": items,
        "pagination": PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    }


# ---------------------------------------------------------------------------
# GET /reviews/approved — public approved reviews (no auth)
# ---------------------------------------------------------------------------

@router.get("/approved", response_model=BaseResponse)
async def get_approved_reviews(
    workspace_id: int = Query(...),
    persona_id: int = Query(..., ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint — returns approved + active reviews with user_name.
    workspace_id and persona_id are both required query params (no JWT on this route).
    Intended for homepage / public-facing widgets.
    """
    service = ReviewService(db)
    reviews = await service.get_approved_reviews(
        workspace_id=workspace_id,
        persona_id=persona_id,
        limit=limit,
    )
    return {"success": True, "message": "Approved reviews retrieved successfully", "data": reviews}


# ---------------------------------------------------------------------------
# GET /reviews/summary — rating summary (protected)
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=BaseResponse)
async def get_rating_summary(
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Return average_rating, total_reviews, and rating_distribution for a persona.
    workspace_id is always resolved from the JWT.
    """
    wid = _require_workspace(current_user)

    service = ReviewService(db)
    summary = await service.get_rating_summary(workspace_id=wid, persona_id=persona_id)
    return {"success": True, "message": "Rating summary retrieved successfully", "data": summary}


# ---------------------------------------------------------------------------
# GET /reviews/{review_id} — single review (protected)
# ---------------------------------------------------------------------------

@router.get("/{review_id}", response_model=BaseResponse)
async def get_review(
    review_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single review by ID, scoped to the caller's workspace and persona.
    Workspace isolation and persona isolation are enforced inside the service call.
    """
    wid = _require_workspace(current_user)

    service = ReviewService(db)
    review = await service.get_review_for_persona(review_id, wid, persona_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return {"success": True, "message": "Review retrieved successfully", "data": review}


# ---------------------------------------------------------------------------
# PUT /reviews/{review_id} — update review (protected)
# ---------------------------------------------------------------------------

@router.put("/{review_id}", response_model=BaseResponse)
async def update_review(
    review_id: int,
    body: ReviewUpdate,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:update")),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a review's rating or comment.
    is_approved is stripped — use the dedicated approve/unapprove endpoints.
    Single DB round-trip: no pre-fetch SELECT.
    """
    wid = _require_workspace(current_user)

    data = body.model_dump(exclude_unset=True)
    data.pop("is_approved", None)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    service = ReviewService(db)
    success = await service.update_review(review_id, wid, persona_id, data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return {"success": True, "message": "Review updated successfully"}


# ---------------------------------------------------------------------------
# PUT /reviews/{review_id}/approve — approve (reviews:manage)
# ---------------------------------------------------------------------------

@router.put("/{review_id}/approve", response_model=BaseResponse)
async def approve_review(
    review_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:manage")),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve a review so it appears publicly.
    Single DB round-trip: no pre-fetch SELECT.
    """
    wid = _require_workspace(current_user)

    service = ReviewService(db)
    success = await service.approve_review(review_id, wid, persona_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return {"success": True, "message": "Review approved successfully"}


# ---------------------------------------------------------------------------
# PUT /reviews/{review_id}/unapprove — unapprove (reviews:manage)
# ---------------------------------------------------------------------------

@router.put("/{review_id}/unapprove", response_model=BaseResponse)
async def unapprove_review(
    review_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:manage")),
    db: AsyncSession = Depends(get_db),
):
    """
    Unapprove a review, hiding it from public view.
    Single DB round-trip: no pre-fetch SELECT.
    """
    wid = _require_workspace(current_user)

    service = ReviewService(db)
    success = await service.unapprove_review(review_id, wid, persona_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return {"success": True, "message": "Review unapproved successfully"}


# ---------------------------------------------------------------------------
# DELETE /reviews/{review_id} — soft delete (reviews:delete)
# ---------------------------------------------------------------------------

@router.delete("/{review_id}", response_model=BaseResponse)
async def delete_review(
    review_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:delete")),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete a review.
    Single DB round-trip: no pre-fetch SELECT.
    """
    wid = _require_workspace(current_user)

    service = ReviewService(db)
    success = await service.soft_delete_review(review_id, wid, persona_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return {"success": True, "message": "Review deleted successfully"}


# ---------------------------------------------------------------------------
# POST /reviews/{review_id}/restore — restore (reviews:manage)
# ---------------------------------------------------------------------------

@router.post("/{review_id}/restore", response_model=BaseResponse)
async def restore_review(
    review_id: int,
    persona_id: int = Query(..., ge=1),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:manage")),
    db: AsyncSession = Depends(get_db),
):
    """
    Restore a soft-deleted review.
    rowcount=0 means the review was not found OR is already active — returns 404 in both cases.
    Single DB round-trip: no pre-fetch SELECT.
    """
    wid = _require_workspace(current_user)

    service = ReviewService(db)
    success = await service.restore_review(review_id, wid, persona_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or is not deleted",
        )
    return {"success": True, "message": "Review restored successfully"}
