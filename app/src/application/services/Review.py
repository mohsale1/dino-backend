"""
ReviewService — business logic for the reviews resource.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.ReviewRepository import ReviewRepository


class ReviewService(BaseService):
    """Service for managing customer reviews."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.review_repo = ReviewRepository(db)
        super().__init__(self.review_repo)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create_review(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and create a new review.

        Reviews are always created with is_approved=False and require
        explicit approval before appearing on the homepage.
        """
        payload = {**data, "is_approved": False}
        payload.setdefault("is_active", True)

        return await self.review_repo.create(payload)

    async def update_review(
        self,
        review_id: int,
        workspace_id: int,
        persona_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """Update allowed fields on an existing review, scoped to persona."""
        allowed_fields = {"rating", "comment", "is_approved"}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_data:
            return False

        return await self.review_repo.update_for_persona(
            review_id, workspace_id, persona_id, update_data
        )

    async def approve_review(
        self,
        review_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Mark a review as approved (visible on homepage), scoped to persona."""
        return await self.review_repo.approve_for_persona(
            review_id, workspace_id, persona_id
        )

    async def unapprove_review(
        self,
        review_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Withdraw approval from a review, scoped to persona."""
        return await self.review_repo.unapprove_for_persona(
            review_id, workspace_id, persona_id
        )

    async def soft_delete_review(
        self,
        review_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Soft-delete a review (sets is_active=False), scoped to persona."""
        return await self.review_repo.soft_delete_for_persona(
            review_id, workspace_id, persona_id
        )

    async def restore_review(
        self,
        review_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> bool:
        """Restore a soft-deleted review (sets is_active=True), scoped to persona."""
        return await self.review_repo.restore_for_persona(
            review_id, workspace_id, persona_id
        )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    async def get_paginated_reviews(
        self,
        workspace_id: int,
        persona_id: int,
        is_approved: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Return a paginated list of reviews enriched with user_name.

        Returns
        -------
        (items, total_count, total_pages)
        """
        items, total, total_pages = await self.review_repo.get_paginated_reviews(
            workspace_id=workspace_id,
            persona_id=persona_id,
            is_approved=is_approved,
            page=page,
            page_size=page_size,
        )
        self._attach_user_name(items)
        return items, total, total_pages

    async def get_approved_reviews(
        self,
        workspace_id: int,
        persona_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Return approved + active reviews for public display, enriched with user_name.
        """
        items = await self.review_repo.get_approved_reviews(
            workspace_id=workspace_id,
            persona_id=persona_id,
            limit=limit,
        )
        self._attach_user_name(items)
        return items

    async def get_rating_summary(
        self,
        workspace_id: int,
        persona_id: int,
    ) -> Dict[str, Any]:
        """Delegate rating statistics to the repository."""
        return await self.review_repo.get_rating_summary(
            workspace_id=workspace_id,
            persona_id=persona_id,
        )

    async def get_review_for_persona(
        self,
        review_id: int,
        workspace_id: int,
        persona_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single review by ID, scoped to workspace and persona."""
        return await self.review_repo.get_by_id_for_persona(
            review_id, workspace_id, persona_id
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _attach_user_name(reviews: List[Dict[str, Any]]) -> None:
        """
        Mutate each review dict in-place: build user_name from the private
        _user_first_name / _user_last_name keys injected by the repository,
        then remove those private keys.

        user_name is None when the review has no associated user.
        """
        for review in reviews:
            first = review.pop("_user_first_name", None)
            last = review.pop("_user_last_name", None)
            if first is not None or last is not None:
                review["user_name"] = f"{first or ''} {last or ''}".strip() or None
            else:
                review["user_name"] = None