"""
Reviews router — CRUD and moderation endpoints for customer reviews.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Review import ReviewService
from src.base.BaseSchema import BaseResponse, PaginatedResponse, PaginationMeta
from src.config.Database import get_db
from src.schemas.Review import ReviewCreate, ReviewResponse, ReviewUpdate

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# ---------------------------------------------------------------------------
# POST /reviews — create a review
# ---------------------------------------------------------------------------

@router.post("", response_model=BaseResponse)
async def create_review(
    body: ReviewCreate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new review. workspace_id resolved from current_user if not provided."""
    data = body.model_dump()
    if not data.get("workspace_id"):
        data["workspace_id"] = current_user.get("workspace_id")
    if not data.get("workspace_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id is required",
        )
    data["user_id"] = current_user.get("id")

    service = ReviewService(db)
    review = await service.create_review(data)
    return {"success": True, "message": "Review created successfully", "data": review}


# ---------------------------------------------------------------------------
# GET /reviews — paginated list (protected)
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse)
async def list_reviews(
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    is_approved: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated reviews. workspace_id resolved from current_user if not provided."""
    wid = workspace_id or current_user.get("workspace_id")
    if not wid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace_id is required",
        )

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
    persona_id: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint — returns approved + active reviews with user_name.
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
    workspace_id: Optional[int] = Query(None),
    persona_id: Optional[int] = Query(None),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:read")),
    db: AsyncSession = Depends(get_db),
):
    """Return average_rating, total_reviews, and rating_distribution."""
    wid = workspace_id or current_user.get("workspace_id")
    service = ReviewService(db)
    summary = await service.get_rating_summary(workspace_id=wid, persona_id=persona_id)
    return {"success": True, "message": "Rating summary retrieved successfully", "data": summary}


# ---------------------------------------------------------------------------
# GET /reviews/{id} — single review (protected)
# ---------------------------------------------------------------------------

@router.get("/{review_id}", response_model=BaseResponse)
async def get_review(
    review_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single review by ID."""
    service = ReviewService(db)
    review = await service.get_by_id(review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if review.get("workspace_id") != current_user.get("workspace_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return {"success": True, "message": "Review retrieved successfully", "data": review}


# ---------------------------------------------------------------------------
# PUT /reviews/{id} — update review (protected)
# ---------------------------------------------------------------------------

@router.put("/{review_id}", response_model=BaseResponse)
async def update_review(
    review_id: int,
    body: ReviewUpdate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a review's rating, comment, or approval status."""
    service = ReviewService(db)
    existing = await service.get_by_id(review_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if existing.get("workspace_id") != current_user.get("workspace_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    data = body.model_dump(exclude_unset=True)
    data.pop("is_approved", None)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    success = await service.update_review(review_id, data)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return {"success": True, "message": "Review updated successfully"}


# ---------------------------------------------------------------------------
# PUT /reviews/{id}/approve — approve (reviews:manage)
# ---------------------------------------------------------------------------

@router.put("/{review_id}/approve", response_model=BaseResponse)
async def approve_review(
    review_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:moderate")),
    db: AsyncSession = Depends(get_db),
):
    """Approve a review so it appears publicly."""
    service = ReviewService(db)
    existing = await service.get_by_id(review_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if existing.get("workspace_id") != current_user.get("workspace_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    success = await service.approve_review(review_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return {"success": True, "message": "Review approved successfully"}


# ---------------------------------------------------------------------------
# PUT /reviews/{id}/unapprove — unapprove (reviews:manage)
# ---------------------------------------------------------------------------

@router.put("/{review_id}/unapprove", response_model=BaseResponse)
async def unapprove_review(
    review_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:moderate")),
    db: AsyncSession = Depends(get_db),
):
    """Unapprove a review, hiding it from public view."""
    service = ReviewService(db)
    existing = await service.get_by_id(review_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if existing.get("workspace_id") != current_user.get("workspace_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    success = await service.unapprove_review(review_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return {"success": True, "message": "Review unapproved successfully"}


# ---------------------------------------------------------------------------
# DELETE /reviews/{id} — soft delete (reviews:delete)
# ---------------------------------------------------------------------------

@router.delete("/{review_id}", response_model=BaseResponse)
async def delete_review(
    review_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a review."""
    service = ReviewService(db)
    existing = await service.get_by_id(review_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if existing.get("workspace_id") != current_user.get("workspace_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    success = await service.soft_delete_review(review_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return {"success": True, "message": "Review deleted successfully"}


# ---------------------------------------------------------------------------
# POST /reviews/{id}/restore — restore (reviews:manage)
# ---------------------------------------------------------------------------

@router.post("/{review_id}/restore", response_model=BaseResponse)
async def restore_review(
    review_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require("reviews:moderate")),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted review."""
    service = ReviewService(db)
    existing = await service.get_by_id(review_id, include_deleted=True)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if existing.get("workspace_id") != current_user.get("workspace_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if existing.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review is not deleted",
        )

    success = await service.restore_review(review_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return {"success": True, "message": "Review restored successfully"}
