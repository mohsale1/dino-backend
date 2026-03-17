"""
Review Routes
Endpoints for managing customer reviews/testimonials
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from src.application.services.Review import ReviewService
from src.core.Dependencies import get_current_user

router = APIRouter(prefix="/reviews", tags=["Reviews"])

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
        raise HTTPException(status_code=404, detail="Review not found")
    
    return {
        "success": True,
        "message": "Review retrieved successfully",
        "data": review
    }

@router.post("")
async def create_review(
    review_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new review
    Requires authentication
    """
    service = ReviewService()
    review = service.create_review(review_data)
    
    return {
        "success": True,
        "message": "Review created successfully",
        "data": review
    }

@router.put("/{review_id}")
async def update_review(
    review_id: str,
    review_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a review
    Requires authentication
    """
    service = ReviewService()
    success = service.update_review(review_id, review_data)
    
    if not success:
        raise HTTPException(status_code=404, detail="Review not found or update failed")
    
    return {
        "success": True,
        "message": "Review updated successfully"
    }

@router.patch("/{review_id}/approve")
async def approve_review(
    review_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Approve a review for public display
    Requires authentication
    """
    service = ReviewService()
    success = service.approve_review(review_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Review not found")
    
    return {
        "success": True,
        "message": "Review approved successfully"
    }

@router.patch("/{review_id}/reject")
async def reject_review(
    review_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Reject/unapprove a review
    Requires authentication
    """
    service = ReviewService()
    success = service.reject_review(review_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Review not found")
    
    return {
        "success": True,
        "message": "Review rejected successfully"
    }

@router.delete("/{review_id}")
async def delete_review(
    review_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Soft delete a review
    Requires authentication
    """
    service = ReviewService()
    success = service.delete_review(review_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Review not found or delete failed")
    
    return {
        "success": True,
        "message": "Review deleted successfully"
    }