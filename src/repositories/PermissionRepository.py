from src.base.BaseRepository import BaseRepository
from typing import Dict, Any, List, Optional, Tuple
from google.cloud.firestore_v1 import FieldFilter
from datetime import datetime, timezone


class PermissionRepository(BaseRepository):
    """Permission repository for database operations"""

    def __init__(self):
        super().__init__("permissions")

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get permission by name"""
        return self.get_by_field("name", name)

    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all permissions by category"""
        return self.get_all(filters={"category": category})

    def get_by_resource(self, resource: str) -> List[Dict[str, Any]]:
        """Get all permissions by resource"""
        return self.get_all(filters={"resource": resource})

    def get_by_action(self, action: str) -> List[Dict[str, Any]]:
        """Get all permissions by action"""
        return self.get_all(filters={"action": action})

    def search(self, query_text: str) -> List[Dict[str, Any]]:
        """
        Search permissions by name or description.
        Note: Firestore doesn't support full-text search natively,
        so we fetch all and filter in memory.
        """
        all_permissions = self.get_all()
        query_lower = query_text.lower()

        results = []
        for perm in all_permissions:
            name = perm.get('name', '').lower()
            description = perm.get('description', '').lower()

            if query_lower in name or query_lower in description:
                results.append(perm)

        return results

    def get_system_permissions(self) -> List[Dict[str, Any]]:
        """Get all system permissions (is_system=True)"""
        return self.get_all(filters={"is_system": True})

    def permission_exists(self, name: str, exclude_id: Optional[str] = None) -> bool:
        """Check if permission with name exists"""
        query = self.collection.where(filter=FieldFilter("name", "==", name))
        query = query.where(filter=FieldFilter("is_deleted", "==", False))

        docs = query.get()

        if not docs:
            return False

        if exclude_id:
            for doc in docs:
                if doc.to_dict().get('id') != exclude_id:
                    return True
            return False

        return True

    def get_paginated_with_filters(
        self,
        page: int = 1,
        page_size: int = 10,
        category: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        is_active: Optional[bool] = None,
        search_query: Optional[str] = None,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Get paginated permissions with advanced filtering.

        Returns: (items, total_count, total_pages)
        """
        query = self.collection
        query = query.where(filter=FieldFilter("is_deleted", "==", False))

        if category:
            query = query.where(filter=FieldFilter("category", "==", category))

        if resource:
            query = query.where(filter=FieldFilter("resource", "==", resource))

        if action:
            query = query.where(filter=FieldFilter("action", "==", action))

        if is_active is not None:
            query = query.where(filter=FieldFilter("is_active", "==", is_active))

        all_docs = query.get()
        all_items = [doc.to_dict() for doc in all_docs]

        if search_query:
            search_lower = search_query.lower()
            all_items = [
                item for item in all_items
                if search_lower in item.get('name', '').lower() or
                   search_lower in item.get('description', '').lower() or
                   search_lower in item.get('resource', '').lower()
            ]

        total = len(all_items)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        reverse = order_direction.lower() == "desc"
        try:
            all_items.sort(key=lambda x: x.get(order_by, ''), reverse=reverse)
        except Exception:
            all_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        items = all_items[start_idx:end_idx]

        return items, total, total_pages

    def bulk_create(self, permissions: List[Dict[str, Any]]) -> List[str]:
        """Bulk create permissions"""
        if not permissions:
            return []

        ids = []
        batch = self.db.batch()

        for perm_data in permissions:
            doc_ref = self.collection.document()
            perm_data['id'] = doc_ref.id
            perm_data['created_at'] = datetime.now(timezone.utc)
            perm_data['updated_at'] = datetime.now(timezone.utc)
            if 'is_active' not in perm_data:
                perm_data['is_active'] = True
            if 'is_deleted' not in perm_data:
                perm_data['is_deleted'] = False

            batch.set(doc_ref, perm_data)
            ids.append(doc_ref.id)

        batch.commit()
        return ids

    def _get_distinct_field_values(self, field: str) -> List[str]:
        """Return sorted distinct non-null values for a given field across all permissions."""
        all_permissions = self.get_all()
        values = {perm[field] for perm in all_permissions if field in perm}
        return sorted(values)

    def get_categories(self) -> List[str]:
        """Get distinct categories"""
        return self._get_distinct_field_values('category')

    def get_resources(self) -> List[str]:
        """Get distinct resources"""
        return self._get_distinct_field_values('resource')

    def get_actions(self) -> List[str]:
        """Get distinct actions"""
        return self._get_distinct_field_values('action')