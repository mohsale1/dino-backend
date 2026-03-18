"""
Review Routes
Endpoints for managing customer reviews/testimonials
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from pydantic import BaseModel, Field
from src.application.services.Review import ReviewService
from src.core.Dependencies import get_current_user
from src.application.middleware.RoleCheck import ApplicationRoleCheck

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class ReviewCreate(BaseModel):
    """Schema for creating a new review"""
    customer_name: str = Field(..., description="Name of the customer")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: str = Field(..., min_length=10, description="Review comment (min 10 characters)")
    role: Optional[str] = Field(None, description="Customer role/title")
    restaurant: Optional[str] = Field(None, description="Restaurant name")
    location: Optional[str] = Field(None, description="Location (city, state)")
    avatar: Optional[str] = Field(None, description="Avatar URL or initials")
    workspace_id: Optional[str] = Field(None, description="Associated workspace ID")
    organization_id: Optional[str] = Field(None, description="Associated organization ID")


class ReviewUpdate(BaseModel):
    """Schema for updating an existing review (all fields optional)"""
    customer_name: Optional[str] = Field(None, description="Name of the customer")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, min_length=10, description="Review comment (min 10 characters)")
    role: Optional[str] = Field(None, description="Customer role/title")
    restaurant: Optional[str] = Field(None, description="Restaurant name")
    location: Optional[str] = Field(None, description="Location (city, state)")
    avatar: Optional[str] = Field(None, description="Avatar URL or initials")
    workspace_id: Optional[str] = Field(None, description="Associated workspace ID")
    organization_id: Optional[str] = Field(None, description="Associated organization ID")


# ============================================================================
# GET ENDPOINTS
# ============================================================================

@router.get("")
async def get_reviews(
    limit: Optional[int] = None,
    workspace_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    approved_only: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """
    Get reviews with optional filters
    Requires authentication
    """
    service = ReviewService()

    if workspace_id:
        reviews = service.get_by_workspace(workspace_id, limit)
    elif organization_id:
        reviews = service.get_by_organization(organization_id, limit)
    elif approved_only:
        reviews = service.get_approved_reviews(limit)
    else:
        reviews = service.get_all_reviews(limit)

    return {
        "success": True,
        "message": "Reviews retrieved successfully",
        "data": reviews
    }


@router.get("/{review_id}")
async def get_review(
    review_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific review by ID
    Requires authentication
    """
    service = ReviewService()
    review = service.get_by_id(review_id)

    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    return {
        "success": True,
        "message": "Review retrieved successfully",
        "data": review
    }


# ============================================================================
# WRITE ENDPOINTS
# ============================================================================

@router.post("")
async def create_review(
    review_data: ReviewCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new review
    Requires authentication
    """
    service = ReviewService()
    data = review_data.model_dump()
    # Tag the review with the creating user's ID for ownership checks
    data['created_by'] = current_user.get('id')
    review = service.create_review(data)

    return {
        "success": True,
        "message": "Review created successfully",
        "data": review
    }


@router.put("/{review_id}")
async def update_review(
    review_id: str,
    review_data: ReviewUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a review.
    Owners may update their own review; managers may update any review.
    Requires authentication
    """
    service = ReviewService()

    # Fetch the existing review to perform ownership check
    existing = service.get_by_id(review_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    user_id = current_user.get('id')
    user_role = current_user.get('role', {}).get('name', '')
    is_manager = user_role in ('Manager', 'Admin', 'SuperAdmin')
    is_owner = existing.get('created_by') == user_id

    if not is_owner and not is_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this review"
        )

    update_payload = review_data.model_dump(exclude_unset=True)
    success = service.update_review(review_id, update_payload)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Review update failed")

    return {
        "success": True,
        "message": "Review updated successfully"
    }


@router.patch("/{review_id}/approve", dependencies=[Depends(ApplicationRoleCheck.require_manager)])
async def approve_review(
    review_id: str,
    current_user: dict = Depends(ApplicationRoleCheck.require_manager)
):
    """
    Approve a review for public display
    Requires Manager role or above
    """
    service = ReviewService()
    success = service.approve_review(review_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    return {
        "success": True,
        "message": "Review approved successfully"
    }


@router.patch("/{review_id}/reject", dependencies=[Depends(ApplicationRoleCheck.require_manager)])
async def reject_review(
    review_id: str,
    current_user: dict = Depends(ApplicationRoleCheck.require_manager)
):
    """
    Reject/unapprove a review
    Requires Manager role or above
    """
    service = ReviewService()
    success = service.reject_review(review_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    return {
        "success": True,
        "message": "Review rejected successfully"
    }


@router.delete("/{review_id}", dependencies=[Depends(ApplicationRoleCheck.require_manager)])
async def delete_review(
    review_id: str,
    current_user: dict = Depends(ApplicationRoleCheck.require_manager)
):
    """
    Soft delete a review
    Requires Manager role or above
    """
    service = ReviewService()
    success = service.delete_review(review_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found or delete failed")

    return {
        "success": True,
        "message": "Review deleted successfully"
    }