from src.base.BaseRepository import BaseRepository
from typing import List, Dict, Any, Optional
from google.cloud.firestore_v1 import FieldFilter, Query


class ReviewRepository(BaseRepository):
    """Review repository"""

    def __init__(self):
        super().__init__("reviews")

    def get_approved_reviews(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get approved reviews ordered by latest"""
        query = self.collection.where(filter=FieldFilter("is_deleted", "==", False)).where(filter=FieldFilter("is_approved", "==", True))
        query = query.order_by("created_at", direction=Query.DESCENDING)

        if limit:
            query = query.limit(limit)

        docs = query.get()
        return [doc.to_dict() for doc in docs]

    def get_by_workspace(self, workspace_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get reviews by workspace"""
        query = self.collection.where(filter=FieldFilter("is_deleted", "==", False)).where(filter=FieldFilter("workspace_id", "==", workspace_id))
        query = query.order_by("created_at", direction=Query.DESCENDING)

        if limit:
            query = query.limit(limit)

        docs = query.get()
        return [doc.to_dict() for doc in docs]

    def get_by_organization(self, organization_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get reviews by organization"""
        query = self.collection.where(filter=FieldFilter("is_deleted", "==", False)).where(filter=FieldFilter("organization_id", "==", organization_id))
        query = query.order_by("created_at", direction=Query.DESCENDING)

        if limit:
            query = query.limit(limit)

        docs = query.get()
        return [doc.to_dict() for doc in docs]