"""
ReviewService — business logic for the reviews resource.
One review per authenticated user per workspace is enforced here and at DB level.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.core.Exceptions import BadRequestError, ConflictError, NotFoundError
from src.repositories.ReviewRepository import ReviewRepository

logger = logging.getLogger(__name__)


class ReviewService(BaseService):
    """Service for managing customer reviews."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.review_repo = ReviewRepository(db)
        super().__init__(self.review_repo)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create_review(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a review. Always starts unapproved.
        Enforces one review per authenticated user per workspace.

        Raises
        ------
        ConflictError
            If the user already has an active review for this workspace.
        """
        workspace_id = data.get("workspace_id")
        user_id = data.get("user_id")

        # Enforce one-review-per-user-per-workspace for authenticated users
        if user_id:
            if await self.review_repo.user_has_review_for_workspace(user_id, workspace_id):
                logger.warning(
                    "review.create.duplicate user_id=%s workspace_id=%s",
                    user_id, workspace_id,
                )
                raise ConflictError(
                    "You have already submitted a review for this workspace. "
                    "Please update your existing review instead."
                )

        payload = {**data, "is_approved": False, "is_active": True}

        try:
            review = await self.review_repo.create(payload)
        except IntegrityError:
            # Catch race condition where two requests slip through simultaneously
            logger.warning(
                "review.create.integrity_error user_id=%s workspace_id=%s",
                user_id, workspace_id,
            )
            raise ConflictError(
                "You have already submitted a review for this workspace."
            )

        logger.info(
            "review.created review_id=%s workspace_id=%s user_id=%s rating=%s",
            review.get("id"), workspace_id, user_id, review.get("rating"),
        )
        return review

    async def update_review(
        self,
        review_id: int,
        workspace_id: int,
        data: Dict[str, Any],
    ) -> bool:
        """
        Update rating/comment on a review, scoped to workspace.
        is_approved is stripped — use approve/unapprove endpoints instead.
        """
        # Strip fields that must not be updated here
        update_data = {k: v for k, v in data.items() if k in {"rating", "comment"}}
        if not update_data:
            raise BadRequestError("No valid fields to update. Allowed: rating, comment")

        updated = await self.review_repo.update_for_workspace(review_id, workspace_id, update_data)
        if updated:
            logger.info(
                "review.updated review_id=%s workspace_id=%s fields=%s",
                review_id, workspace_id, list(update_data.keys()),
            )
        else:
            logger.warning(
                "review.update.not_found review_id=%s workspace_id=%s",
                review_id, workspace_id,
            )
        return updated

    async def approve_review(self, review_id: int, workspace_id: int) -> bool:
        updated = await self.review_repo.approve_for_workspace(review_id, workspace_id)
        if updated:
            logger.info(
                "review.approved review_id=%s workspace_id=%s",
                review_id, workspace_id,
            )
        return updated

    async def unapprove_review(self, review_id: int, workspace_id: int) -> bool:
        updated = await self.review_repo.unapprove_for_workspace(review_id, workspace_id)
        if updated:
            logger.info(
                "review.unapproved review_id=%s workspace_id=%s",
                review_id, workspace_id,
            )
        return updated

    async def soft_delete_review(self, review_id: int, workspace_id: int) -> bool:
        deleted = await self.review_repo.soft_delete_for_workspace(review_id, workspace_id)
        if deleted:
            logger.info(
                "review.deleted review_id=%s workspace_id=%s",
                review_id, workspace_id,
            )
        return deleted

    async def restore_review(self, review_id: int, workspace_id: int) -> bool:
        """
        Restore a soft-deleted review.
        Re-checks the one-review-per-user constraint before restoring.
        """
        # Fetch the deleted review to get user_id
        review = await self.review_repo.get_by_id_for_workspace(
            review_id, workspace_id, include_deleted=True
        )
        if not review:
            return False

        if review.get("is_active"):
            raise BadRequestError("Review is not deleted")

        user_id = review.get("user_id")
        if user_id:
            if await self.review_repo.user_has_review_for_workspace(
                user_id, workspace_id, exclude_id=review_id
            ):
                logger.warning(
                    "review.restore.conflict review_id=%s user_id=%s workspace_id=%s",
                    review_id, user_id, workspace_id,
                )
                raise ConflictError(
                    "Cannot restore: this user already has an active review for this workspace."
                )

        restored = await self.review_repo.restore_for_workspace(review_id, workspace_id)
        if restored:
            logger.info(
                "review.restored review_id=%s workspace_id=%s",
                review_id, workspace_id,
            )
        return restored

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_paginated_reviews(
        self,
        workspace_id: int,
        is_approved: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Return paginated reviews — COUNT + DATA run in parallel."""
        logger.debug(
            "review.list workspace_id=%s is_approved=%s page=%s page_size=%s",
            workspace_id, is_approved, page, page_size,
        )
        result = await self.review_repo.get_paginated_reviews(
            workspace_id=workspace_id,
            is_approved=is_approved,
            page=page,
            page_size=page_size,
        )
        logger.debug(
            "review.list.result workspace_id=%s total=%s returned=%s",
            workspace_id, result[1], len(result[0]),
        )
        return result

    async def get_approved_reviews(
        self, workspace_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Return approved + active reviews for public display."""
        reviews = await self.review_repo.get_approved_reviews(
            workspace_id=workspace_id, limit=limit
        )
        logger.debug(
            "review.approved workspace_id=%s limit=%s returned=%s",
            workspace_id, limit, len(reviews),
        )
        return reviews

    async def get_rating_summary(self, workspace_id: int) -> Dict[str, Any]:
        """Return average_rating and total_reviews."""
        summary = await self.review_repo.get_rating_summary(workspace_id=workspace_id)
        logger.debug(
            "review.summary workspace_id=%s avg=%s total=%s",
            workspace_id, summary.get("average_rating"), summary.get("total_reviews"),
        )
        return summary

    async def get_review_for_workspace(
        self, review_id: int, workspace_id: int
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single review by ID scoped to workspace."""
        return await self.review_repo.get_by_id_for_workspace(review_id, workspace_id)
