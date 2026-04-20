"""
Review Service
Business logic for managing reviews/testimonials
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from src.repositories.ReviewRepository import ReviewRepository


class ReviewService:
    """Service for review management"""

    def __init__(self, db: AsyncSession):
        self.review_repo = ReviewRepository(db)

    async def get_all_reviews(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all reviews"""
        return await self.review_repo.get_all(limit=limit)

    async def get_approved_reviews(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get approved reviews ordered by latest"""
        return await self.review_repo.get_approved_reviews(limit=limit)

    async def get_by_workspace(self, workspace_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get reviews by workspace"""
        return await self.review_repo.get_by_workspace(workspace_id, limit)

    async def get_by_persona(self, persona_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get reviews by organization"""
        return await self.review_repo.get_by_persona(persona_id, limit)

    async def get_by_id(self, review_id: str) -> Optional[Dict[str, Any]]:
        """Get review by ID"""
        return await self.review_repo.get_by_id(review_id)

    async def create_review(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new review"""
        if 'is_approved' not in review_data:
            review_data['is_approved'] = False

        if 'rating' not in review_data:
            review_data['rating'] = 5

        return await self.review_repo.create(review_data)

    async def update_review(self, review_id: str, review_data: Dict[str, Any]) -> bool:
        """Update a review"""
        return await self.review_repo.update(review_id, review_data)

    async def approve_review(self, review_id: str) -> bool:
        """Approve a review for public display"""
        return await self.review_repo.update(review_id, {'is_approved': True})

    async def reject_review(self, review_id: str) -> bool:
        """Reject/unapprove a review"""
        return await self.review_repo.update(review_id, {'is_approved': False})

    async def delete_review(self, review_id: str) -> bool:
        """Soft delete a review"""
        return await self.review_repo.soft_delete(review_id)
