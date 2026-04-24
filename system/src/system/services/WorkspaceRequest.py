from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.base.BaseService import BaseService
from src.repositories.UserRepository import UserRepository
from src.repositories.WorkspaceRepository import WorkspaceRepository
from src.repositories.WorkspaceRequestRepository import WorkspaceRequestRepository


class WorkspaceRequestService(BaseService):
    """Business logic for workspace join requests."""

    def __init__(self, db: AsyncSession) -> None:
        self.workspace_request_repo = WorkspaceRequestRepository(db)
        self.user_repo = UserRepository(db)
        self.workspace_repo = WorkspaceRepository(db)
        super().__init__(self.workspace_request_repo)

    async def submit_request(self, data: dict) -> dict:
        """Submit a new workspace join request."""
        email: str = data["email"]
        workspace_id: int = data["workspace_id"]

        user: Optional[Dict] = await self.user_repo.get_by_field("email", email)
        if not user or user.get("user_type") != 0 or not user.get("is_active"):
            raise HTTPException(
                status_code=422,
                detail="Email does not belong to an active system user",
            )

        has_pending: bool = await self.workspace_request_repo.has_pending_request(workspace_id)
        if has_pending:
            raise HTTPException(
                status_code=409,
                detail="A pending request already exists for this workspace",
            )

        record = await self.create(
            {
                "email": email,
                "user_id": user["id"],
                "workspace_id": workspace_id,
                "status": "pending",
            }
        )
        return record

    async def get_paginated_requests(
        self,
        status: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List, int, int]:
        """Return paginated workspace requests filtered by status."""
        return await self.workspace_request_repo.get_paginated_requests(status, page, page_size)

    async def get_request(self, request_id: int) -> Optional[dict]:
        """Fetch a single workspace request by id."""
        return await self.get_by_id(request_id)

    async def approve_request(self, request_id: int, reviewed_by_user_id: int) -> dict:
        """Approve a pending workspace request and verify the workspace."""
        request: Optional[dict] = await self.get_by_id(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")

        if request.get("status") != "pending":
            raise HTTPException(status_code=409, detail="Request is not pending")

        await self.update(
            request_id,
            {
                "status": "approved",
                "reviewed_by": reviewed_by_user_id,
                "reviewed_at": datetime.now(timezone.utc),
            },
        )

        await self.workspace_repo.update(
            request["workspace_id"],
            {
                "is_verified": True,
                "requested_by": request["user_id"],
            },
        )

        return await self.get_by_id(request_id)

    async def reject_request(
        self,
        request_id: int,
        reviewed_by_user_id: int,
        rejection_reason: Optional[str],
    ) -> dict:
        """Reject a pending workspace request."""
        request: Optional[dict] = await self.get_by_id(request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")

        if request.get("status") != "pending":
            raise HTTPException(status_code=409, detail="Request is not pending")

        await self.update(
            request_id,
            {
                "status": "rejected",
                "reviewed_by": reviewed_by_user_id,
                "reviewed_at": datetime.now(timezone.utc),
                "rejection_reason": rejection_reason,
            },
        )

        return await self.get_by_id(request_id)