"""
Reviews router — CRUD and moderation endpoints for customer reviews.

Architecture:
  - One review per authenticated user per workspace (enforced at DB + service level)
  - Reviews start unapproved — staff must explicitly approve for public display
  - Public endpoint (GET /reviews/approved) requires no auth
  - All staff endpoints require authentication
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.middleware.RoleCheck import ApplicationPermissionCheck
from src.application.services.Review import ReviewService
from src.base.BaseSchema import BaseResponse
from src.config.Database import get_db
from src.core.Exceptions import BadRequestError, NotFoundError
from src.schemas.Review import ReviewCreate, ReviewUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _require_workspace(current_user: Dict[str, Any]) -> int:
    wid = current_user.get("workspace_id")
    if not wid:
        raise BadRequestError("workspace_id could not be resolved for this user")
    return wid


# ---------------------------------------------------------------------------
# POST /reviews  — create
# ---------------------------------------------------------------------------

@router.post("", response_model=BaseResponse, status_code=201)
async def create_review(
    body: ReviewCreate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a review for the caller's workspace.
    One review per user per workspace — returns 409 if already submitted.
    Always starts unapproved.
    """
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "reviews.create.request user_id=%s workspace_id=%s rating=%s",
        user_id, workspace_id, body.rating,
    )

    data = body.model_dump()
    data["workspace_id"] = workspace_id
    data["user_id"] = user_id

    review = await ReviewService(db).create_review(data)

    logger.info(
        "reviews.create.response user_id=%s workspace_id=%s review_id=%s rating=%s",
        user_id, workspace_id, review.get("id"), review.get("rating"),
    )
    return {"success": True, "message": "Review submitted successfully. It will appear after approval.", "data": review}


# ---------------------------------------------------------------------------
# GET /reviews  — paginated list (staff)
# ---------------------------------------------------------------------------

@router.get("", response_model=BaseResponse)
async def list_reviews(
    is_approved: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated reviews scoped to the caller's workspace."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "reviews.list.request user_id=%s workspace_id=%s "
        "is_approved=%s page=%s page_size=%s",
        user_id, workspace_id, is_approved, page, page_size,
    )

    items, total, total_pages = await ReviewService(db).get_paginated_reviews(
        workspace_id=workspace_id,
        is_approved=is_approved,
        page=page,
        page_size=page_size,
    )

    logger.info(
        "reviews.list.response user_id=%s workspace_id=%s "
        "total=%s page=%s total_pages=%s returned=%s",
        user_id, workspace_id, total, page, total_pages, len(items),
    )
    return {
        "success": True,
        "message": "Reviews retrieved successfully",
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


# ---------------------------------------------------------------------------
# GET /reviews/approved  — public, no auth
# ---------------------------------------------------------------------------

@router.get("/approved", response_model=BaseResponse)
async def get_approved_reviews(
    workspace_id: int = Query(..., ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — returns approved + active reviews for a workspace."""
    logger.info(
        "reviews.approved.request workspace_id=%s limit=%s",
        workspace_id, limit,
    )

    reviews = await ReviewService(db).get_approved_reviews(
        workspace_id=workspace_id,
        limit=limit,
    )

    logger.info(
        "reviews.approved.response workspace_id=%s returned=%s",
        workspace_id, len(reviews),
    )
    return {"success": True, "message": "Approved reviews retrieved successfully", "data": reviews}


# ---------------------------------------------------------------------------
# GET /reviews/summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=BaseResponse)
async def get_rating_summary(
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Return average_rating and total_reviews for the caller's workspace."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "reviews.summary.request user_id=%s workspace_id=%s",
        user_id, workspace_id,
    )

    summary = await ReviewService(db).get_rating_summary(workspace_id=workspace_id)

    logger.info(
        "reviews.summary.response user_id=%s workspace_id=%s avg=%s total=%s",
        user_id, workspace_id,
        summary.get("average_rating"), summary.get("total_reviews"),
    )
    return {"success": True, "message": "Rating summary retrieved successfully", "data": summary}


# ---------------------------------------------------------------------------
# GET /reviews/{review_id}
# ---------------------------------------------------------------------------

@router.get("/{review_id}", response_model=BaseResponse)
async def get_review(
    review_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Get a single review by ID, scoped to the caller's workspace."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "reviews.get.request user_id=%s workspace_id=%s review_id=%s",
        user_id, workspace_id, review_id,
    )

    review = await ReviewService(db).get_review_for_workspace(review_id, workspace_id)
    if not review:
        logger.warning(
            "reviews.get.not_found user_id=%s workspace_id=%s review_id=%s",
            user_id, workspace_id, review_id,
        )
        raise NotFoundError("Review not found")

    logger.info(
        "reviews.get.response user_id=%s review_id=%s rating=%s is_approved=%s",
        user_id, review_id, review.get("rating"), review.get("is_approved"),
    )
    return {"success": True, "message": "Review retrieved successfully", "data": review}


# ---------------------------------------------------------------------------
# PUT /reviews/{review_id}  — update rating/comment
# ---------------------------------------------------------------------------

@router.put("/{review_id}", response_model=BaseResponse)
async def update_review(
    review_id: int,
    body: ReviewUpdate,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Update a review's rating or comment. Cannot change approval status here."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    data = body.model_dump(exclude_unset=True)
    data.pop("is_approved", None)  # approval managed via dedicated endpoints only

    if not data:
        logger.warning(
            "reviews.update.empty_payload user_id=%s review_id=%s",
            user_id, review_id,
        )
        raise BadRequestError("No valid fields to update. Allowed: rating, comment")

    logger.info(
        "reviews.update.request user_id=%s workspace_id=%s "
        "review_id=%s fields=%s",
        user_id, workspace_id, review_id, list(data.keys()),
    )

    success = await ReviewService(db).update_review(review_id, workspace_id, data)
    if not success:
        raise NotFoundError("Review not found")

    logger.info(
        "reviews.update.response user_id=%s review_id=%s fields=%s",
        user_id, review_id, list(data.keys()),
    )
    return {"success": True, "message": "Review updated successfully"}


# ---------------------------------------------------------------------------
# PUT /reviews/{review_id}/approve
# ---------------------------------------------------------------------------

@router.put("/{review_id}/approve", response_model=BaseResponse)
async def approve_review(
    review_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Approve a review so it appears publicly."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "reviews.approve.request user_id=%s workspace_id=%s review_id=%s",
        user_id, workspace_id, review_id,
    )

    success = await ReviewService(db).approve_review(review_id, workspace_id)
    if not success:
        raise NotFoundError("Review not found")

    logger.info(
        "reviews.approve.response user_id=%s workspace_id=%s review_id=%s",
        user_id, workspace_id, review_id,
    )
    return {"success": True, "message": "Review approved successfully"}


# ---------------------------------------------------------------------------
# PUT /reviews/{review_id}/unapprove
# ---------------------------------------------------------------------------

@router.put("/{review_id}/unapprove", response_model=BaseResponse)
async def unapprove_review(
    review_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Unapprove a review, hiding it from public view."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "reviews.unapprove.request user_id=%s workspace_id=%s review_id=%s",
        user_id, workspace_id, review_id,
    )

    success = await ReviewService(db).unapprove_review(review_id, workspace_id)
    if not success:
        raise NotFoundError("Review not found")

    logger.info(
        "reviews.unapprove.response user_id=%s workspace_id=%s review_id=%s",
        user_id, workspace_id, review_id,
    )
    return {"success": True, "message": "Review unapproved successfully"}


# ---------------------------------------------------------------------------
# DELETE /reviews/{review_id}
# ---------------------------------------------------------------------------

@router.delete("/{review_id}", response_model=BaseResponse)
async def delete_review(
    review_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a review."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "reviews.delete.request user_id=%s workspace_id=%s review_id=%s",
        user_id, workspace_id, review_id,
    )

    success = await ReviewService(db).soft_delete_review(review_id, workspace_id)
    if not success:
        logger.warning(
            "reviews.delete.not_found user_id=%s workspace_id=%s review_id=%s",
            user_id, workspace_id, review_id,
        )
        raise NotFoundError("Review not found")

    logger.info(
        "reviews.delete.response user_id=%s workspace_id=%s review_id=%s",
        user_id, workspace_id, review_id,
    )
    return {"success": True, "message": "Review deleted successfully"}


# ---------------------------------------------------------------------------
# POST /reviews/{review_id}/restore
# ---------------------------------------------------------------------------

@router.post("/{review_id}/restore", response_model=BaseResponse)
async def restore_review(
    review_id: int,
    current_user: Dict[str, Any] = Depends(ApplicationPermissionCheck.require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted review. Re-checks one-review constraint before restoring."""
    user_id = current_user.get("id")
    workspace_id = _require_workspace(current_user)

    logger.info(
        "reviews.restore.request user_id=%s workspace_id=%s review_id=%s",
        user_id, workspace_id, review_id,
    )

    success = await ReviewService(db).restore_review(review_id, workspace_id)
    if not success:
        logger.warning(
            "reviews.restore.not_found user_id=%s workspace_id=%s review_id=%s",
            user_id, workspace_id, review_id,
        )
        raise NotFoundError("Review not found or is not deleted")

    logger.info(
        "reviews.restore.response user_id=%s workspace_id=%s review_id=%s",
        user_id, workspace_id, review_id,
    )
    return {"success": True, "message": "Review restored successfully"}
