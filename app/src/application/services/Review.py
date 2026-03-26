"""
Review Service
Business logic for managing reviews/testimonials
"""

from typing import Dict, Any, List, Optional
from src.repositories.ReviewRepository import ReviewRepository


class ReviewService:
    """Service for review management"""
    
    def __init__(self):
        self.review_repo = ReviewRepository()
    
    def get_all_reviews(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all reviews"""
        return self.review_repo.get_all(limit=limit)
    
    def get_approved_reviews(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get approved reviews ordered by latest"""
        return self.review_repo.get_approved_reviews(limit=limit)
    
    def get_by_workspace(self, workspace_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get reviews by workspace"""
        return self.review_repo.get_by_workspace(workspace_id, limit)
    
    def get_by_organization(self, organization_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get reviews by organization"""
        return self.review_repo.get_by_organization(organization_id, limit)
    
    def get_by_id(self, review_id: str) -> Optional[Dict[str, Any]]:
        """Get review by ID"""
        return self.review_repo.get_by_id(review_id)
    
    def create_review(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new review"""
        # Set default values
        if 'is_approved' not in review_data:
            review_data['is_approved'] = False  # Reviews need approval by default
        
        if 'rating' not in review_data:
            review_data['rating'] = 5
        
        return self.review_repo.create(review_data)
    
    def update_review(self, review_id: str, review_data: Dict[str, Any]) -> bool:
        """Update a review"""
        return self.review_repo.update(review_id, review_data)
    
    def approve_review(self, review_id: str) -> bool:
        """Approve a review for public display"""
        return self.review_repo.update(review_id, {"is_approved": True})
    
    def reject_review(self, review_id: str) -> bool:
        """Reject/unapprove a review"""
        return self.review_repo.update(review_id, {"is_approved": False})
    
    def delete_review(self, review_id: str) -> bool:
        """Soft delete a review"""
        return self.review_repo.soft_delete(review_id)
